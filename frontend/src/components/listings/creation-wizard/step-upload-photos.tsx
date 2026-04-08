"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { useToast } from "@/components/ui/toast";
import apiClient from "@/lib/api-client";
import { sha256 } from "@/lib/hash";
import type { WizardFormData } from "./wizard-container";

const MAX_FILES = 100;
const MAX_SIZE_MB = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png"];
const ACCEPTED_EXTENSIONS = ".jpg,.jpeg,.png";

interface FileEntry {
  file: File;
  preview: string;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepUploadPhotos({ formData, onUpdate, onNext, onBack }: Props) {
  const { toast } = useToast();
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<{ total: number; completed: number; status: string } | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const listingId = formData.listingId!;

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const toAdd: FileEntry[] = [];
      const errors: string[] = [];

      for (const file of Array.from(newFiles)) {
        if (!ACCEPTED_TYPES.includes(file.type)) {
          errors.push(`${file.name}: invalid type (JPG/PNG only)`);
          continue;
        }
        if (file.size > MAX_SIZE_BYTES) {
          errors.push(`${file.name}: exceeds ${MAX_SIZE_MB}MB limit`);
          continue;
        }
        toAdd.push({
          file,
          preview: URL.createObjectURL(file),
          progress: 0,
          status: "pending",
        });
      }

      if (errors.length > 0) {
        toast(errors.join("\n"), "error");
      }

      setFiles((prev) => {
        const combined = [...prev, ...toAdd];
        if (combined.length > MAX_FILES) {
          toast(`Max ${MAX_FILES} files. ${combined.length - MAX_FILES} dropped.`, "error");
          return combined.slice(0, MAX_FILES);
        }
        return combined;
      });
    },
    [toast]
  );

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      e.target.value = "";
    }
  }

  function removeFile(index: number) {
    setFiles((prev) => {
      URL.revokeObjectURL(prev[index].preview);
      return prev.filter((_, i) => i !== index);
    });
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setUploading(true);

    try {
      // 1. Get presigned upload URLs
      const filenames = files.map((f) => f.file.name);
      const { urls } = await apiClient.getUploadUrls(listingId, filenames);

      // 2. Upload each file via presigned URL (POST multipart or PUT)
      const uploadPromises = urls.map(async (urlInfo, i) => {
        setFiles((prev) =>
          prev.map((f, j) => (j === i ? { ...f, status: "uploading" } : f))
        );

        try {
          await new Promise<void>((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const presigned = urlInfo.upload_url as unknown as {
              url: string;
              fields: Record<string, string>;
            };

            if (typeof presigned === "object" && presigned.fields) {
              // S3 multipart POST
              xhr.open("POST", presigned.url);
              const fd = new FormData();
              Object.entries(presigned.fields).forEach(([k, v]) => fd.append(k, v));
              fd.append("file", files[i].file);

              xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                  const pct = Math.round((e.loaded / e.total) * 100);
                  setFiles((prev) =>
                    prev.map((f, j) => (j === i ? { ...f, progress: pct } : f))
                  );
                }
              };
              xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                  setFiles((prev) =>
                    prev.map((f, j) =>
                      j === i ? { ...f, status: "done", progress: 100 } : f
                    )
                  );
                  resolve();
                } else {
                  reject(new Error(`Upload failed: ${xhr.status}`));
                }
              };
              xhr.onerror = () => reject(new Error("Network error"));
              xhr.send(fd);
            } else {
              // Plain PUT
              xhr.open("PUT", urlInfo.upload_url as unknown as string);
              xhr.setRequestHeader("Content-Type", urlInfo.content_type);
              xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                  const pct = Math.round((e.loaded / e.total) * 100);
                  setFiles((prev) =>
                    prev.map((f, j) => (j === i ? { ...f, progress: pct } : f))
                  );
                }
              };
              xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                  setFiles((prev) =>
                    prev.map((f, j) =>
                      j === i ? { ...f, status: "done", progress: 100 } : f
                    )
                  );
                  resolve();
                } else {
                  reject(new Error(`Upload failed: ${xhr.status}`));
                }
              };
              xhr.onerror = () => reject(new Error("Network error"));
              xhr.send(files[i].file);
            }
          });

          return { key: urlInfo.key, file: files[i].file };
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Upload failed";
          setFiles((prev) =>
            prev.map((f, j) => (j === i ? { ...f, status: "error", error: msg } : f))
          );
          return null;
        }
      });

      const results = await Promise.all(uploadPromises);
      const successful = results.filter(Boolean) as { key: string; file: File }[];

      if (successful.length === 0) {
        toast("All uploads failed", "error");
        setUploading(false);
        return;
      }

      // 3. Hash and register assets
      const assets = await Promise.all(
        successful.map(async ({ key, file }) => ({
          file_path: key,
          file_hash: await sha256(file),
        }))
      );

      const registered = await apiClient.registerAssets(listingId, { assets });

      // Store uploaded assets in wizard state using local blob previews for thumbnails
      const returnedAssets = (registered as any).assets ?? [];
      const newUploaded = returnedAssets.map((a: any, i: number) => ({
        id: a.id,
        filename: successful[i]?.file?.name ?? a.file_path ?? "",
        url: files[i]?.preview ?? URL.createObjectURL(successful[i].file),
      }));
      onUpdate({
        uploadedAssets: [...formData.uploadedAssets, ...newUploaded],
      });

      toast(
        `${successful.length} photo${successful.length > 1 ? "s" : ""} uploaded`,
        "success"
      );

      // Don't revoke blob URLs — they're used for thumbnails in the wizard
      setFiles([]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast(msg, "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleImportLink() {
    if (!importUrl.trim() || !listingId) return;
    setImporting(true);
    setImportError(null);
    setImportProgress(null);
    try {
      const result = await apiClient.importFromLink(listingId, importUrl.trim());
      const pollId = setInterval(async () => {
        try {
          const status = await apiClient.getImportStatus(listingId, result.import_id);
          setImportProgress({ total: status.total_files, completed: status.completed_files, status: status.status });
          if (status.status === "completed" || status.status === "failed") {
            clearInterval(pollId);
            setImporting(false);
            if (status.status === "failed") {
              setImportError(status.error_message || "Import failed");
            } else {
              toast(`${status.completed_files} photo${status.completed_files !== 1 ? "s" : ""} imported`, "success");
              setImportUrl("");
              setImportProgress(null);
              // Refresh uploaded assets list
              try {
                const assets = await apiClient.getAssets(listingId);
                const mapped = assets.map((a) => ({
                  id: a.id,
                  filename: a.file_path?.split("/").pop() ?? "",
                  url: a.thumbnail_url ?? "",
                }));
                onUpdate({ uploadedAssets: mapped });
              } catch {
                // Fallback: just trigger next step
              }
            }
          }
        } catch {
          clearInterval(pollId);
          setImporting(false);
          setImportError("Failed to check import status");
        }
      }, 2000);
    } catch (err) {
      setImporting(false);
      setImportError(err instanceof Error ? err.message : "Import failed");
    }
  }

  const canProceed = formData.uploadedAssets.length > 0;

  return (
    <GlassCard tilt={false}>
      <h2
        className="text-xl font-bold mb-2"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        Upload Photos
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)] mb-6">
        JPG or PNG · max {MAX_SIZE_MB}MB each · up to {MAX_FILES} files
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragOver(false); }}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleDrop(e); }}
      >
        <div
          onClick={() => inputRef.current?.click()}
          className={`
            relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
            transition-colors duration-200
            ${
              dragOver
                ? "border-[var(--color-primary)] bg-blue-50/50"
                : "border-[var(--color-border)] hover:border-[var(--color-primary)]/50 hover:bg-white/30"
            }
          `}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED_EXTENSIONS}
            onChange={handleFileInput}
            className="hidden"
          />
          <svg
            className="w-10 h-10 mx-auto mb-3 text-[var(--color-text-secondary)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Drag photos here or{" "}
            <span className="text-[var(--color-primary)] font-medium">browse</span>
          </p>
        </div>

        {/* Pending file grid */}
        <AnimatePresence>
          {files.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 mt-4">
                {files.map((entry, i) => (
                  <div
                    key={i}
                    className="relative group aspect-square rounded-lg overflow-hidden bg-slate-100"
                  >
                    <img
                      src={entry.preview}
                      alt={entry.file.name}
                      className="w-full h-full object-cover"
                    />
                    {entry.status === "uploading" && (
                      <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                        <div className="w-3/4 h-1.5 bg-white/30 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-white rounded-full transition-all duration-200"
                            style={{ width: `${entry.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                    {entry.status === "done" && (
                      <div className="absolute inset-0 bg-green-500/20 flex items-center justify-center">
                        <span className="text-white text-lg">✓</span>
                      </div>
                    )}
                    {entry.status === "error" && (
                      <div className="absolute inset-0 bg-red-500/30 flex items-center justify-center">
                        <span className="text-white text-lg">✕</span>
                      </div>
                    )}
                    {!uploading && (
                      <button
                        onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                        className="absolute top-1 right-1 w-5 h-5 bg-black/60 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-[var(--color-text-secondary)]">
                  {files.length} file{files.length !== 1 ? "s" : ""} selected
                </span>
                <div className="flex gap-2">
                  {!uploading && (
                    <Button
                      variant="secondary"
                      onClick={() => {
                        files.forEach((f) => URL.revokeObjectURL(f.preview));
                        setFiles([]);
                      }}
                    >
                      Clear
                    </Button>
                  )}
                  <Button onClick={handleUpload} loading={uploading}>
                    Upload {files.length} Photo{files.length !== 1 ? "s" : ""}
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Import from Link */}
      <div className="mt-6 pt-6 border-t border-slate-100">
        <p className="text-sm text-slate-500 mb-3">
          Or import directly from a delivery link
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Paste Google Drive, Dropbox, or Show & Tour link..."
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
            disabled={importing}
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-200 bg-white text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all"
          />
          <button
            onClick={handleImportLink}
            disabled={importing || !importUrl.trim()}
            className="px-4 py-2.5 rounded-lg bg-[#F97316] text-white text-sm font-medium hover:bg-[#EA580C] disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap transition-colors"
          >
            {importing ? "Importing..." : "Import"}
          </button>
        </div>
        {importProgress && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>{importProgress.status === "running" ? "Downloading photos..." : importProgress.status}</span>
              <span>{importProgress.completed}/{importProgress.total}</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#F97316] rounded-full transition-all duration-300"
                style={{ width: importProgress.total > 0 ? `${(importProgress.completed / importProgress.total) * 100}%` : "0%" }}
              />
            </div>
          </div>
        )}
        {importError && (
          <p className="mt-2 text-sm text-red-500">{importError}</p>
        )}
        <p className="mt-2 text-xs text-slate-400">
          Supports Google Drive, Dropbox shared folders, and Show &amp; Tour delivery links
        </p>
      </div>

      {/* Already-uploaded summary */}
      {formData.uploadedAssets.length > 0 && (
        <div className="mt-6 pt-5 border-t border-[var(--color-border)]">
          <p className="text-sm font-medium mb-3">
            {formData.uploadedAssets.length} photo
            {formData.uploadedAssets.length !== 1 ? "s" : ""} uploaded
          </p>
          <div className="grid grid-cols-6 sm:grid-cols-8 gap-1.5">
            {formData.uploadedAssets.slice(0, 16).map((asset) => (
              <div
                key={asset.id}
                className="aspect-square rounded-md overflow-hidden bg-slate-100"
              >
                {asset.url ? (
                  <img
                    src={asset.url}
                    alt={asset.filename}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}
              </div>
            ))}
            {formData.uploadedAssets.length > 16 && (
              <div className="aspect-square rounded-md bg-slate-100 flex items-center justify-center text-xs text-slate-500 font-medium">
                +{formData.uploadedAssets.length - 16}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-8 pt-4 border-t border-[var(--color-border)]">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext} disabled={!canProceed}>
          Next: Virtual Staging
        </Button>
      </div>

      {!canProceed && (
        <p className="text-xs text-center text-[var(--color-text-secondary)] mt-2">
          Upload at least one photo to continue.
        </p>
      )}
    </GlassCard>
  );
}
