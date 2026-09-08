#!/usr/bin/env bash
# aws_decommission.sh — tear down the ListingJet AWS footprint and stop all charges.
#
# Context: ListingJet has migrated off AWS (code-complete) to Render + Supabase +
# Upstash + Cloudflare R2 + Temporal Cloud. This pre-launch deployment holds only
# throwaway test data, so the whole AWS footprint can be deleted. This script does
# that in cost-priority order and ends with a scan for resources that silently keep
# billing (unattached EIPs, orphan EBS/snapshots).
#
# IMPORTANT — your own CDK config has two traps this script handles for you:
#   - RDS has deletion_protection=True + removal_policy=RETAIN  (infra/stacks/database.py)
#   - the S3 media bucket defaults to RETAIN
#   => `cdk destroy` ALONE WOULD ORPHAN THE DB + BUCKET AND KEEP BILLING.
#   This script deletes the stateful resources directly instead.
#
# Usage:
#   bash scripts/aws_decommission.sh                 # DRY RUN — prints what it would delete
#   bash scripts/aws_decommission.sh --execute       # actually delete (asks for confirmation)
#   bash scripts/aws_decommission.sh --execute --no-snapshot   # skip the final RDS snapshot
#
# Flags:
#   --execute       perform deletions (default is dry-run / read-only)
#   --no-snapshot   delete RDS without a final snapshot (default: take one)
#   --region REGION AWS region (default: us-east-1)
#   --yes           skip the interactive "type DELETE" confirmation (for unattended runs)
#
# Requires: awscli v2, authenticated to the ListingJet account.

set -uo pipefail

REGION="us-east-1"
EXECUTE=false
TAKE_SNAPSHOT=true
ASSUME_YES=false
CLUSTER="listingjet"
RDS_ID="listingjet-postgres-encrypted"
OLD_SNAPSHOT="handoff-safety-20260414-0830"
ECR_REPOS=("listingjet-api" "listingjet-worker")
S3_BUCKET_GLOB="listingjet-media"

while [ $# -gt 0 ]; do
  case "$1" in
    --execute) EXECUTE=true ;;
    --no-snapshot) TAKE_SNAPSHOT=false ;;
    --yes) ASSUME_YES=true ;;
    --region) REGION="$2"; shift ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
  shift
done

export AWS_PAGER=""
DATESTAMP="$(date +%Y%m%d-%H%M)"

# ── helpers ───────────────────────────────────────────────────────────────────
say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }

# run: echo the command; only execute it when --execute is set. Never aborts the
# script on a single failed delete (resources may already be gone / mid-delete).
run() {
  if $EXECUTE; then
    info "RUN: $*"
    "$@" || info "  (non-fatal: command returned $?)"
  else
    info "DRY: $*"
  fi
}

require_aws() {
  command -v aws >/dev/null || { echo "awscli not found"; exit 1; }
  local who
  who=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null) \
    || { echo "ERROR: AWS credentials not configured / not authenticated."; exit 1; }
  say "Account: $who   Region: $REGION"
  if ! $EXECUTE; then
    info "MODE: DRY RUN (read-only). Re-run with --execute to delete."
  else
    info "MODE: EXECUTE — resources WILL be deleted."
  fi
}

confirm() {
  $ASSUME_YES && return 0
  $EXECUTE || return 0
  echo
  echo "This permanently deletes the ListingJet AWS deployment in $REGION."
  read -r -p "Type DELETE to proceed: " ans
  [ "$ans" = "DELETE" ] || { echo "Aborted."; exit 1; }
}

# ── 0. RDS: lift deletion protection (must precede delete) ──────────────────────
prep_rds() {
  say "[0] RDS — disable deletion protection on $RDS_ID"
  if aws rds describe-db-instances --db-instance-identifier "$RDS_ID" --region "$REGION" >/dev/null 2>&1; then
    run aws rds modify-db-instance --db-instance-identifier "$RDS_ID" \
      --no-deletion-protection --apply-immediately --region "$REGION"
  else
    info "RDS instance $RDS_ID not found (already deleted?) — skipping."
  fi
}

# ── 1. ECS Fargate (biggest always-on cost) ─────────────────────────────────────
kill_ecs() {
  say "[1] ECS — drain + delete services, then the cluster ($CLUSTER)"
  if ! aws ecs describe-clusters --clusters "$CLUSTER" --region "$REGION" \
        --query 'clusters[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
    info "Cluster $CLUSTER not active — skipping."
    return
  fi
  local svcs
  svcs=$(aws ecs list-services --cluster "$CLUSTER" --region "$REGION" \
          --query 'serviceArns[]' --output text 2>/dev/null)
  for arn in $svcs; do
    local name=${arn##*/}
    info "service: $name"
    run aws ecs update-service --cluster "$CLUSTER" --service "$name" --desired-count 0 --region "$REGION"
    run aws ecs delete-service --cluster "$CLUSTER" --service "$name" --force --region "$REGION"
  done
  run aws ecs delete-cluster --cluster "$CLUSTER" --region "$REGION"
}

# ── 2. NAT Gateways + their Elastic IPs ─────────────────────────────────────────
kill_nat() {
  say "[2] NAT Gateways (+ release their EIPs)"
  local nats
  nats=$(aws ec2 describe-nat-gateways --region "$REGION" \
          --filter Name=state,Values=available,pending \
          --query 'NatGateways[].NatGatewayId' --output text 2>/dev/null)
  [ -z "$nats" ] && { info "No active NAT gateways."; return; }
  for n in $nats; do
    info "nat: $n"
    run aws ec2 delete-nat-gateway --nat-gateway-id "$n" --region "$REGION"
  done
  info "NAT deletion is async (~1-2 min). EIPs are released in the final scan once detached."
}

# ── 3. Application Load Balancers + target groups ───────────────────────────────
kill_alb() {
  say "[3] Load balancers + target groups (tagged for ListingJet)"
  local lbs
  lbs=$(aws elbv2 describe-load-balancers --region "$REGION" \
         --query 'LoadBalancers[].LoadBalancerArn' --output text 2>/dev/null)
  for lb in $lbs; do
    # only touch LBs tagged by the CDK stack
    if aws elbv2 describe-tags --resource-arns "$lb" --region "$REGION" \
         --query 'TagDescriptions[0].Tags[?starts_with(Value,`ListingJet`)]' \
         --output text 2>/dev/null | grep -qi listingjet; then
      info "alb: ${lb##*/}"
      run aws elbv2 delete-load-balancer --load-balancer-arn "$lb" --region "$REGION"
    fi
  done
  local tgs
  tgs=$(aws elbv2 describe-target-groups --region "$REGION" \
         --query 'TargetGroups[?starts_with(TargetGroupName,`Listi`) || contains(TargetGroupName,`listingjet`)].TargetGroupArn' \
         --output text 2>/dev/null)
  for tg in $tgs; do
    info "target-group: ${tg##*/}"
    run aws elbv2 delete-target-group --target-group-arn "$tg" --region "$REGION"
  done
}

# ── 4. RDS instance + leftover snapshots ────────────────────────────────────────
kill_rds() {
  say "[4] RDS — delete $RDS_ID"
  if aws rds describe-db-instances --db-instance-identifier "$RDS_ID" --region "$REGION" >/dev/null 2>&1; then
    if $TAKE_SNAPSHOT; then
      run aws rds delete-db-instance --db-instance-identifier "$RDS_ID" \
        --final-db-snapshot-identifier "listingjet-final-$DATESTAMP" --region "$REGION"
      info "(final snapshot: listingjet-final-$DATESTAMP — delete it later once you're sure)"
    else
      run aws rds delete-db-instance --db-instance-identifier "$RDS_ID" \
        --skip-final-snapshot --delete-automated-backups --region "$REGION"
    fi
  else
    info "RDS instance not found — skipping."
  fi
  # old pre-migration safety-net snapshot still incurs storage charges
  if aws rds describe-db-snapshots --db-snapshot-identifier "$OLD_SNAPSHOT" --region "$REGION" >/dev/null 2>&1; then
    run aws rds delete-db-snapshot --db-snapshot-identifier "$OLD_SNAPSHOT" --region "$REGION"
  fi
}

# ── 5. ElastiCache (Redis) ──────────────────────────────────────────────────────
kill_elasticache() {
  say "[5] ElastiCache — delete ListingJet Redis"
  local rgs
  rgs=$(aws elasticache describe-replication-groups --region "$REGION" \
         --query 'ReplicationGroups[?contains(ReplicationGroupId,`listingjet`) || contains(Description,`istingJet`)].ReplicationGroupId' \
         --output text 2>/dev/null)
  for rg in $rgs; do
    info "replication-group: $rg"
    run aws elasticache delete-replication-group --replication-group-id "$rg" --region "$REGION"
  done
  local ccs
  ccs=$(aws elasticache describe-cache-clusters --region "$REGION" \
         --query 'CacheClusters[?contains(CacheClusterId,`listingjet`)].CacheClusterId' \
         --output text 2>/dev/null)
  for cc in $ccs; do
    info "cache-cluster: $cc"
    run aws elasticache delete-cache-cluster --cache-cluster-id "$cc" --region "$REGION"
  done
  [ -z "$rgs$ccs" ] && info "No ListingJet ElastiCache resources found."
}

# ── 6. CloudFront (disable then delete; deletion needs a 2nd pass) ──────────────
kill_cloudfront() {
  say "[6] CloudFront — disable ListingJet distributions"
  local ids
  ids=$(aws cloudfront list-distributions \
         --query "DistributionList.Items[?contains(Comment,'listingjet') || contains(Comment,'ListingJet')].Id" \
         --output text 2>/dev/null)
  [ -z "$ids" ] && { info "No ListingJet CloudFront distributions found."; return; }
  for id in $ids; do
    info "distribution: $id"
    if $EXECUTE; then
      local etag cfg
      etag=$(aws cloudfront get-distribution-config --id "$id" --query 'ETag' --output text)
      cfg=$(aws cloudfront get-distribution-config --id "$id" --query 'DistributionConfig' --output json \
            | python3 -c "import sys,json;c=json.load(sys.stdin);c['Enabled']=False;print(json.dumps(c))")
      echo "$cfg" > "/tmp/cf-$id.json"
      run aws cloudfront update-distribution --id "$id" --if-match "$etag" \
        --distribution-config "file:///tmp/cf-$id.json"
      info "  disabled. CloudFront takes ~10-15 min to deploy 'Disabled'."
      info "  AFTER it shows Deployed+Disabled, delete with:"
      info "    ETAG=\$(aws cloudfront get-distribution-config --id $id --query ETag --output text)"
      info "    aws cloudfront delete-distribution --id $id --if-match \$ETAG"
    else
      info "DRY: would disable then (after deploy) delete distribution $id"
    fi
  done
}

# ── 7. S3, ECR, Secrets, CloudWatch logs ────────────────────────────────────────
kill_storage_misc() {
  say "[7a] S3 — empty + delete ListingJet media buckets"
  local buckets
  buckets=$(aws s3api list-buckets --query "Buckets[?starts_with(Name,'$S3_BUCKET_GLOB')].Name" --output text 2>/dev/null)
  for b in $buckets; do
    info "bucket: $b"
    run aws s3 rm "s3://$b" --recursive --region "$REGION"
    run aws s3api delete-bucket --bucket "$b" --region "$REGION"
  done
  [ -z "$buckets" ] && info "No matching buckets."

  say "[7b] ECR — delete repos"
  for r in "${ECR_REPOS[@]}"; do
    if aws ecr describe-repositories --repository-names "$r" --region "$REGION" >/dev/null 2>&1; then
      run aws ecr delete-repository --repository-name "$r" --force --region "$REGION"
    fi
  done

  say "[7c] Secrets Manager — delete ListingJet secrets"
  local secs
  secs=$(aws secretsmanager list-secrets --region "$REGION" \
          --query "SecretList[?contains(Name,'listingjet') || contains(Name,'ListingJet')].Name" \
          --output text 2>/dev/null)
  for s in $secs; do
    info "secret: $s"
    run aws secretsmanager delete-secret --secret-id "$s" --force-delete-without-recovery --region "$REGION"
  done
  [ -z "$secs" ] && info "No ListingJet secrets found."

  say "[7d] CloudWatch — delete /listingjet/* log groups"
  local lgs
  lgs=$(aws logs describe-log-groups --log-group-name-prefix "/listingjet" --region "$REGION" \
         --query 'logGroups[].logGroupName' --output text 2>/dev/null)
  for lg in $lgs; do
    run aws logs delete-log-group --log-group-name "$lg" --region "$REGION"
  done
  [ -z "$lgs" ] && info "No /listingjet log groups found."
}

# ── 8. Final billing-leftover scan (always runs, read-only) ─────────────────────
scan_leftovers() {
  say "[8] LEFTOVER SCAN — these silently keep billing if present"
  info "Unattached Elastic IPs (release these):"
  aws ec2 describe-addresses --region "$REGION" \
    --query 'Addresses[?AssociationId==null].[AllocationId,PublicIp]' --output text 2>/dev/null | sed 's/^/    /'
  if $EXECUTE; then
    for alloc in $(aws ec2 describe-addresses --region "$REGION" \
                    --query 'Addresses[?AssociationId==null].AllocationId' --output text 2>/dev/null); do
      run aws ec2 release-address --allocation-id "$alloc" --region "$REGION"
    done
  fi
  info "Available (orphan) EBS volumes:"
  aws ec2 describe-volumes --region "$REGION" --filters Name=status,Values=available \
    --query 'Volumes[].[VolumeId,Size]' --output text 2>/dev/null | sed 's/^/    /'
  info "Manual RDS snapshots remaining:"
  aws rds describe-db-snapshots --snapshot-type manual --region "$REGION" \
    --query 'DBSnapshots[].DBSnapshotIdentifier' --output text 2>/dev/null | sed 's/^/    /'
  info "EC2 snapshots owned by you:"
  aws ec2 describe-snapshots --owner-ids self --region "$REGION" \
    --query 'Snapshots[].[SnapshotId,VolumeSize]' --output text 2>/dev/null | sed 's/^/    /'
  info "Remaining NAT gateways:"
  aws ec2 describe-nat-gateways --region "$REGION" \
    --filter Name=state,Values=available,pending \
    --query 'NatGateways[].NatGatewayId' --output text 2>/dev/null | sed 's/^/    /'
  say "Done. Check Billing → Cost Explorer tomorrow; it should trend to ~\$0."
  info "Note: VPC/subnets/IGW themselves are free; leave them or delete the"
  info "ListingJetNetwork CFN stack last if you want a spotless account."
}

# ── main ────────────────────────────────────────────────────────────────────────
require_aws
confirm
prep_rds
kill_ecs
kill_nat
kill_alb
kill_rds
kill_elasticache
kill_cloudfront
kill_storage_misc
scan_leftovers
