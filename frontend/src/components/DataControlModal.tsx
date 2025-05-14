// frontend/src/components/DataControlModal.tsx
"use client";

import React from 'react';
import Modal from './Modal';

interface DataControlModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmDelete: () => void; // Callback for when user confirms deletion
}

const DataControlModal: React.FC<DataControlModalProps> = ({ isOpen, onClose, onConfirmDelete }) => {
  const handleDelete = () => {
    // Actual deletion logic will be triggered by onConfirmDelete
    onConfirmDelete();
    onClose(); // Close modal after confirming
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Data Control">
      <div className="space-y-4">
        <p className="text-gray-700 font-medium">
          Are you sure you want to delete all your personalized learning data?
        </p>
        <p className="text-sm text-gray-500">
          This includes:
        </p>
        <ul className="list-disc list-inside text-sm text-gray-500 space-y-1">
          <li>All questions you've answered</li>
          <li>Your scores and points history</li>
          <li>Your list of incorrectly answered questions</li>
        </ul>
        <p className="text-sm text-red-600 font-semibold">
          This action cannot be undone.
        </p>
        <div className="flex justify-end space-x-3 pt-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Yes, Delete My Data
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default DataControlModal;