// frontend/src/components/Navbar.tsx
"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import Image from "next/image";
import { useState, useEffect, useRef } from "react";
import SetAvatarModal from "./SetAvatarModal";
import DataControlModal from "./DataControlModal";

// Updated UserAvatar to show initials based on session data
const UserAvatarPlaceholder: React.FC<{
  name?: string | null;
  email?: string | null;
}> = ({ name, email }) => {
  const getInitials = () => {
    if (name) {
      const parts = name.split(" ");
      if (parts.length > 1 && parts[0] && parts[parts.length - 1]) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
      }
      if (parts[0] && parts[0][0]) {
        return parts[0][0].toUpperCase();
      }
    }
    if (email && email[0]) {
      return email[0].toUpperCase();
    }
    return "U";
  };

  return (
    <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white text-lg font-semibold border-2 border-gray-200">
      {getInitials()}
    </div>
  );
};

export default function Navbar() {
  const { data: session, status } = useSession();
  console.log("Navbar rendering. Session user image:", session?.user?.image);

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [isSetAvatarModalOpen, setIsSetAvatarModalOpen] = useState(false);
  const [isDataControlModalOpen, setIsDataControlModalOpen] = useState(false);

  const toggleDropdown = () => setIsDropdownOpen(!isDropdownOpen);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownRef]);

  const handleOpenSetAvatarModal = () => {
    setIsSetAvatarModalOpen(true);
    setIsDropdownOpen(false);
  };

  const handleOpenDataControlModal = () => {
    setIsDataControlModalOpen(true);
    setIsDropdownOpen(false);
  };

  const handleConfirmDeleteData = async () => {
    if (!session?.idToken) {
      alert("Authentication token not found. Please sign in again.");
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/api/users/me/data`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${session.idToken}`,
          },
        }
      );

      if (response.ok) {
        alert("Your personalized learning data has been successfully deleted. You will be logged out.");
        // Optionally, clear local session state or redirect
        signOut({ callbackUrl: "/" }); // Sign out and redirect to home
      } else {
        const errorData = await response.json();
        alert(
          `Failed to delete data: ${errorData.detail || response.statusText}`
        );
      }
    } catch (error) {
      console.error("Error deleting user data:", error);
      alert("An error occurred while trying to delete your data.");
    }
    setIsDataControlModalOpen(false); // Close modal regardless of outcome
  };

  if (status === "loading") {
    return (
      <header className="bg-gray-800 text-white p-4 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
          <Link href="/home" className="text-xl font-bold">
            EngMCQ
          </Link>
          <div>Loading...</div>
        </div>
      </header>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <>
      <header className="bg-white text-gray-700 p-4 shadow-md w-full top-0 z-50">
        <div className="container mx-auto flex justify-between items-center">
          <Link
            href="/home"
            className="text-2xl font-bold text-blue-600 hover:text-blue-700"
          >
            EngMCQ Platform
          </Link>
          <nav className="relative" ref={dropdownRef}>
            {session.user ? (
              <button
                onClick={toggleDropdown}
                className="focus:outline-none rounded-full"
              >
                {session.user.image ? (
                  <Image
                    src={session.user.image}
                    alt={session.user.name || "User Avatar"}
                    width={40}
                    height={40}
                    className="rounded-full border-2 border-gray-300 hover:border-blue-500"
                    key={session.user.image}
                  />
                ) : (
                  <UserAvatarPlaceholder
                    name={session.user.name}
                    email={session.user.email}
                  />
                )}
              </button>
            ) : null}
            {isDropdownOpen && session.user && (
              <div className="absolute right-0 mt-2 w-60 bg-white rounded-md shadow-xl py-1 z-[60] border border-gray-200">
                <div className="px-4 py-3 text-sm text-gray-500 border-b">
                  Signed in as <br />
                  <strong className="text-gray-700 truncate">
                    {session.user.name || session.user.email}
                  </strong>
                </div>
                <button
                  onClick={handleOpenSetAvatarModal}
                  className="w-full text-left block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Set Avatar
                </button>
                <button
                  onClick={handleOpenDataControlModal}
                  className="w-full text-left block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Data Control
                </button>
                <div className="border-t border-gray-100 my-1"></div>
                <button
                  onClick={() => {
                    signOut({ callbackUrl: "/" });
                    setIsDropdownOpen(false);
                  }}
                  className="w-full text-left block px-4 py-2 text-sm text-red-600 hover:bg-red-50 hover:text-red-700"
                >
                  Sign Out
                </button>
              </div>
            )}
          </nav>
        </div>
      </header>

      <SetAvatarModal
        isOpen={isSetAvatarModalOpen}
        onClose={() => setIsSetAvatarModalOpen(false)}
      />
      <DataControlModal
        isOpen={isDataControlModalOpen}
        onClose={() => setIsDataControlModalOpen(false)}
        onConfirmDelete={handleConfirmDeleteData}
      />
    </>
  );
}
