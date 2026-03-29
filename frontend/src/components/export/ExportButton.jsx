import React, { useState } from 'react';
import ExportDialog from './ExportDialog';
import './ExportButton.css';

const ExportButton = ({ entityType = 'inventory', filters = null, label = 'Export' }) => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <button
        onClick={() => setShowDialog(true)}
        className="export-button-main"
        title={`Export ${entityType}`}
      >
        📥 {label}
      </button>

      <ExportDialog
        entityType={entityType}
        filters={filters}
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
      />
    </>
  );
};

export default ExportButton;
