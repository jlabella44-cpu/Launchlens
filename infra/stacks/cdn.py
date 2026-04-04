"""CloudFront CDN distribution for S3 media assets."""

from aws_cdk import (
    CfnOutput,
    Stack,
)
from aws_cdk import (
    aws_cloudfront as cloudfront,
)
from aws_cdk import (
    aws_cloudfront_origins as origins,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct


class ListingJetCDN(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        media_bucket: s3.IBucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Origin Access Identity to keep the bucket private
        oai = cloudfront.OriginAccessIdentity(
            self, "MediaOAI",
            comment="OAI for ListingJet media bucket",
        )
        media_bucket.grant_read(oai)

        # CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self, "MediaDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    media_bucket,
                    origin_access_identity=oai,
                ),
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                compress=True,
            ),
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            comment="ListingJet media CDN",
        )

        CfnOutput(
            self, "DistributionDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront distribution domain name for media assets",
        )
