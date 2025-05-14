// frontend/src/components/SetAvatarModal.tsx
"use client";

import React, { useState, ChangeEvent, useRef, useEffect } from "react"; // Added useEffect
import Modal from "./Modal";
import Image from "next/image";
import { useSession, getSession, signOut } from "next-auth/react"; // Added getSession
import { useRouter } from "next/navigation";

interface SetAvatarModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SetAvatarModal: React.FC<SetAvatarModalProps> = ({ isOpen, onClose }) => {
  const { data: session, update: updateSession } = useSession();
  const router = useRouter(); // Keep if you plan to use router.refresh()
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null); // Initialize to null
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Effect to update previewUrl when modal opens or session image changes
  useEffect(() => {
    if (isOpen) {
      // When modal opens, reset to current session avatar or null
      setPreviewUrl(session?.user?.image || null);
      setSelectedFile(null); // Clear any previously selected file
      setError(null); // Clear previous errors
      setIsUploading(false); // Reset uploading state
    }
  }, [isOpen, session?.user?.image]); // Depend on isOpen and session image

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        // Max 2MB
        setError("File is too large. Maximum size is 2MB.");
        setSelectedFile(null);
        // Do not revert previewUrl here, let user see their selection was invalid
        return;
      }
      if (
        !["image/png", "image/jpeg", "image/gif", "image/webp"].includes(
          file.type
        )
      ) {
        setError(
          "Invalid file type. Please select a PNG, JPG, GIF, or WEBP image."
        );
        setSelectedFile(null);
        // Do not revert previewUrl here
        return;
      }
      setError(null);
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSaveAvatar = async () => {
    if (!selectedFile) {
      setError("Please select an image file.");
      return;
    }
    if (!session?.user?.id) {
      setError("User session not found. Please try logging in again.");
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(
        "http://localhost:8000/api/users/me/avatar",
        {
          method: "PUT",
          body: formData,
          headers: {
            // @ts-ignore
            "X-User-ID": session.user.id,
          },
        }
      );

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (e) {
          errorData = { detail: `Server error: ${response.status}` };
        }
        console.error("Server error details:", errorData);
        throw new Error(errorData.detail || "Failed to upload avatar.");
      }

      const result = await response.json();
      console.log("Backend response for avatar upload:", result);

      if (result.avatarUrl) {
        const cacheBustedUrl = `${result.avatarUrl}${result.avatarUrl.includes('?') ? '&' : '?'}v=${Date.now()}`;
        console.log("Attempting to update session with URL:", cacheBustedUrl);
        await updateSession({
          user: {
            // @ts-ignore
            ...session.user,
            image: cacheBustedUrl,
          },
        });
        console.log("updateSession called.");

        router.refresh();
        console.log("router.refresh() was called.");
        alert(result.message || "Avatar updated successfully!"); // Moved here
        onClose(); // Moved here
      } else {
        console.error("avatarUrl not found in backend response");
        const errorMessage = result.message || "Failed to get new avatar URL from server.";
        setError(errorMessage);
        alert(errorMessage);
        onClose();
      }

      // The following alert and onClose have been moved into the conditional blocks above.
      // alert(result.message || "Avatar updated successfully!");
      // onClose();
    } catch (err: any) {
      console.error("Avatar upload error:", err);
      setError(err.message || "An unexpected error occurred during upload.");
    } finally {
      setIsUploading(false);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Set Your Avatar" size="md">
      <div className="space-y-6">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-32 h-32 rounded-full overflow-hidden border-2 border-gray-300 flex items-center justify-center bg-gray-100">
            {previewUrl ? (
              <Image
                src={previewUrl}
                alt="Avatar Preview"
                width={128}
                height={128}
                className="object-cover w-full h-full"
                key={previewUrl}
              />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-16 h-16 text-gray-400"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
                />
              </svg>
            )}
          </div>
          <button
            type="button"
            onClick={triggerFileInput}
            disabled={isUploading}
            className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-100 rounded-md hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {selectedFile ? "Change Image" : "Select Image"}
          </button>
          <input
            type="file"
            ref={fileInputRef}
            id="avatar-upload"
            name="avatar-upload"
            accept="image/png, image/jpeg, image/gif, image/webp"
            onChange={handleFileChange}
            className="hidden"
            disabled={isUploading}
          />
        </div>

        {error && <p className="text-sm text-red-600 text-center">{error}</p>}

        <div className="flex justify-end space-x-3 pt-2 border-t border-gray-200 mt-6">
          <button
            type="button"
            onClick={onClose}
            disabled={isUploading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSaveAvatar}
            disabled={!selectedFile || isUploading} // Save button disabled if no file or uploading
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {isUploading ? (
              <div className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Uploading...
              </div>
            ) : (
              "Save Avatar"
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default SetAvatarModal;
