// frontend/src/components/ResetDashboardConfirmationModal.tsx
"use client";

import React from 'react';
import Modal from './Modal'; // Assuming Modal.tsx is in the same directory

interface ResetDashboardConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
}

const ResetDashboardConfirmationModal: React.FC<ResetDashboardConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading = false,
}) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Reset Dashboard Data?" size="md">
      <div className="py-4">
        <p className="text-gray-700 mb-6">
          Are you sure you want to reset all your dashboard data? This action will clear your total points, points history, and your list of incorrectly answered questions. This cannot be undone.
        </p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50 disabled:bg-red-400"
          >
            {isLoading ? 'Resetting...' : 'Confirm Reset'}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default ResetDashboardConfirmationModal;
