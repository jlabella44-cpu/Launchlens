"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

const MAX_FILES = 50;
const MIN_FILES = 5;
const MAX_SIZE_MB = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png"];
const ACCEPTED_EXTENSIONS = ".jpg,.jpeg,.png";

interface FileEntry {
  file: File;
  preview: string;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
}

export default function DemoPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [uploadProgress, setUploadProgress] = useState("");

  useEffect(() => { document.title = "Try ListingJet — Free Demo"; }, []);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const toAdd: FileEntry[] = [];
    const errors: string[] = [];

    for (const file of Array.from(newFiles)) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        errors.push(`${file.name}: JPG or PNG only`);
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        errors.push(`${file.name}: exceeds ${MAX_SIZE_MB}MB`);
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
      setError(errors.join(". "));
    }

    setFiles((prev) => {
      const combined = [...prev, ...toAdd];
      if (combined.length > MAX_FILES) {
        setError(`Maximum ${MAX_FILES} photos. Extra files removed.`);
        return combined.slice(0, MAX_FILES);
      }
      return combined;
    });
  }, []);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    setError("");
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      setError("");
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
    if (files.length < MIN_FILES) {
      setError(`At least ${MIN_FILES} photos required. You have ${files.length}.`);
      return;
    }

    setUploading(true);
    setError("");
    setUploadProgress("Creating demo listing...");

    try {
      // 1. Create demo listing and get presigned upload URLs
      const createRes = await apiClient.demoCreate(files.length);
      const { demo_id, upload_urls } = createRes;

      // 2. Upload each file to S3
      const uploadedKeys: string[] = [];
      for (let i = 0; i < files.length; i++) {
        setUploadProgress(`Uploading photo ${i + 1} of ${files.length}...`);
        setFiles((prev) =>
          prev.map((f, j) => (j === i ? { ...f, status: "uploading" } : f))
        );

        const urlInfo = upload_urls[i];
        if (!urlInfo?.upload_url) {
          setFiles((prev) =>
            prev.map((f, j) => (j === i ? { ...f, status: "error" } : f))
          );
          continue;
        }

        try {
          const presigned = urlInfo.upload_url;
          await new Promise<void>((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            if (typeof presigned === "object" && presigned.fields) {
              xhr.open("POST", presigned.url);
              const fd = new FormData();
              Object.entries(presigned.fields).forEach(([k, v]) => fd.append(k, v as string));
              fd.append("file", files[i].file);

              xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                  const pct = Math.round((e.loaded / e.total) * 100);
                  setFiles((prev) =>
                    prev.map((f, j) => (j === i ? { ...f, progress: pct } : f))
                  );
                }
              };
              xhr.onload = () => (xhr.status < 300 ? resolve() : reject(new Error(`${xhr.status}`)));
              xhr.onerror = () => reject(new Error("Network error"));
              xhr.send(fd);
            } else {
              reject(new Error("Invalid upload URL format"));
            }
          });

          setFiles((prev) =>
            prev.map((f, j) => (j === i ? { ...f, status: "done", progress: 100 } : f))
          );
          uploadedKeys.push(urlInfo.key);
        } catch {
          setFiles((prev) =>
            prev.map((f, j) => (j === i ? { ...f, status: "error" } : f))
          );
        }
      }

      if (uploadedKeys.length < MIN_FILES) {
        setError(`Only ${uploadedKeys.length} photos uploaded successfully. Need at least ${MIN_FILES}.`);
        setUploading(false);
        return;
      }

      // 3. Finalize the demo
      setUploadProgress("Processing your photos...");
      await apiClient.demoFinalize(demo_id, uploadedKeys);

      // 4. Navigate to results
      files.forEach((f) => URL.revokeObjectURL(f.preview));
      router.push(`/demo/${demo_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
      setUploading(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 flex flex-col items-center px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-3xl w-full"
        >
          {/* Hero */}
          <div className="text-center mb-8">
            <h1
              className="text-4xl font-bold text-[var(--color-text)] mb-3"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              See AI Results in Minutes
            </h1>
            <p className="text-lg text-[var(--color-text-secondary)]">
              Drop your listing photos below. Our AI will curate, score, and package them — no account needed.
            </p>
          </div>

          <GlassCard tilt={false} className="text-left">
            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); }}
              onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); }}
              onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(false); }}
              onDrop={(e) => { e.stopPropagation(); handleDrop(e); }}
            >
              <div
                onClick={() => !uploading && inputRef.current?.click()}
                className={`
                  relative border-2 border-dashed rounded-xl p-8 text-center transition-colors duration-200
                  ${uploading ? "cursor-default" : "cursor-pointer"}
                  ${dragOver
                    ? "border-[#F97316] bg-orange-50/50"
                    : "border-[var(--color-border)] hover:border-[#F97316]/50 hover:bg-white/30"
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
                  disabled={uploading}
                />
                <svg className="w-10 h-10 mx-auto mb-3 text-[var(--color-text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  <span className="text-[#F97316] font-semibold">Drag &amp; drop photos here</span> or click to browse
                </p>
                <p className="text-xs text-slate-400 mt-2">
                  JPG or PNG · max {MAX_SIZE_MB}MB each · {MIN_FILES}–{MAX_FILES} photos
                </p>
              </div>

              {/* Photo previews */}
              <AnimatePresence>
                {files.length > 0 && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 gap-2 mt-4">
                      {files.map((entry, i) => (
                        <div key={i} className="relative group aspect-square rounded-lg overflow-hidden bg-slate-100">
                          <img
                            src={entry.preview}
                            alt={entry.file.name}
                            className="w-full h-full object-cover"
                          />
                          {/* Progress overlay */}
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
                              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                          )}
                          {entry.status === "error" && (
                            <div className="absolute inset-0 bg-red-500/30 flex items-center justify-center">
                              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </div>
                          )}
                          {/* Remove button */}
                          {!uploading && (
                            <button
                              onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                              className="absolute top-1 right-1 w-5 h-5 bg-black/60 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                            >
                              ×
                            </button>
                          )}
                          {/* File name */}
                          <span className="absolute bottom-0 inset-x-0 bg-black/50 text-white text-[8px] px-1 py-0.5 truncate">
                            {entry.file.name}
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center justify-between mt-4">
                      <span className="text-sm text-[var(--color-text-secondary)]">
                        {files.length} photo{files.length !== 1 ? "s" : ""} selected
                        {files.length < MIN_FILES && (
                          <span className="text-yellow-600 ml-1">
                            (need {MIN_FILES - files.length} more)
                          </span>
                        )}
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
                            Clear All
                          </Button>
                        )}
                        <Button
                          onClick={handleUpload}
                          loading={uploading}
                          disabled={files.length < MIN_FILES}
                        >
                          {uploading ? uploadProgress : `Process ${files.length} Photos`}
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {error && (
              <p className="text-red-500 text-sm mt-3">{error}</p>
            )}
          </GlassCard>

          {/* How it works */}
          <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { step: "1", title: "Drop Photos", desc: "Drag and drop your listing photos — JPG or PNG, up to 50 files." },
              { step: "2", title: "AI Processes", desc: "Our AI curates, scores, and packages the best shots in minutes." },
              { step: "3", title: "Review Results", desc: "See your AI-curated package. Create an account to unlock all features." },
            ].map((item) => (
              <div key={item.step} className="text-center p-4">
                <div className="w-8 h-8 rounded-full bg-[#F97316] text-white text-sm font-bold flex items-center justify-center mx-auto mb-3">
                  {item.step}
                </div>
                <h3 className="text-sm font-semibold text-[var(--color-text)] mb-1">{item.title}</h3>
                <p className="text-xs text-[var(--color-text-secondary)]">{item.desc}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </main>
    </>
  );
}
