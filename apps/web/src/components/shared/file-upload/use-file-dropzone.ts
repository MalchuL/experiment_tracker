"use client";

import { useCallback, useRef } from "react";

export function useFileDropzone(onFiles: (files: FileList) => void) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBoxClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      if (event.dataTransfer.files.length > 0) {
        onFiles(event.dataTransfer.files);
      }
    },
    [onFiles]
  );

  const handleFileSelect = useCallback(
    (files: FileList | null) => {
      if (files && files.length > 0) {
        onFiles(files);
      }
    },
    [onFiles]
  );

  const resetFileInput = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  return {
    fileInputRef,
    handleBoxClick,
    handleDragOver,
    handleDrop,
    handleFileSelect,
    resetFileInput,
  };
}
