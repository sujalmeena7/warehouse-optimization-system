import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Download, Upload, AlertCircle, CheckCircle, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/hooks/useAuth";
import { warehouseApi } from "@/lib/api";

export default function ImportPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState("containers");
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [errors, setErrors] = useState([]);
  const [fileToUpload, setFileToUpload] = useState(null);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      toast.error("Please select a CSV file");
      return;
    }

    setFileToUpload(file);
    setImportResult(null);
    setErrors([]);
  }, []);

  const downloadTemplate = async (type) => {
    try {
      setUploading(true);
      let blob;
      if (type === "containers") {
        blob = await warehouseApi.downloadContainersTemplate();
      } else {
        blob = await warehouseApi.downloadInventoryTemplate();
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}-template.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`${type} template downloaded`);
    } catch (error) {
      toast.error(`Failed to download ${type} template`);
    } finally {
      setUploading(false);
    }
  };

  const handleImport = async () => {
    if (!fileToUpload) {
      toast.error("Please select a file first");
      return;
    }

    if (!user) {
      toast.error("Not authenticated");
      return;
    }

    setImporting(true);
    setErrors([]);
    setImportResult(null);

    try {
      let result;
      if (tab === "containers") {
        result = await warehouseApi.importContainers(fileToUpload);
      } else {
        result = await warehouseApi.importInventory(fileToUpload);
      }

      setImportResult(result);
      setFileToUpload(null);

      if (result.errors && result.errors.length > 0) {
        setErrors(result.errors);
        toast.warning(`Imported with ${result.errors.length} errors`);
      } else {
        toast.success(`Successfully imported ${result.success_count || result.imported_count || 0} ${tab}`);
      }
    } catch (error) {
      const errorDetail = error?.response?.data?.detail || error?.message || "Import failed";
      toast.error(errorDetail);
      setErrors([
        {
          row: "general",
          error: errorDetail,
        },
      ]);
    } finally {
      setImporting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
      data-testid="import-page-root"
    >
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="font-heading text-2xl" data-testid="import-title">
            Bulk Data Import
          </CardTitle>
          <p className="text-sm text-slate-600" data-testid="import-subtitle">
            Import containers and inventory from CSV files. Download templates to see the required format.
          </p>
        </CardHeader>
      </Card>

      <Tabs value={tab} onValueChange={setTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="containers">Containers</TabsTrigger>
          <TabsTrigger value="inventory">Inventory</TabsTrigger>
        </TabsList>

        <TabsContent value="containers" className="space-y-4">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg">Import Containers</CardTitle>
              <p className="text-sm text-slate-600">
                Upload a CSV file with container data. Required columns: container_id, size, weight, access_frequency
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="outline"
                onClick={() => downloadTemplate("containers")}
                disabled={uploading}
                className="w-full gap-2"
              >
                <Download className="h-4 w-4" />
                {uploading ? "Downloading..." : "Download Template"}
              </Button>

              <ImportUploadArea
                tab={tab}
                fileToUpload={fileToUpload}
                onFileSelect={handleFileSelect}
                onImport={handleImport}
                importing={importing}
              />

              {importResult && <ImportResults result={importResult} type="containers" />}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="inventory" className="space-y-4">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg">Import Inventory</CardTitle>
              <p className="text-sm text-slate-600">
                Upload a CSV file with inventory items. Required columns: sku, name, category, zone, bin_code, x, y, quantity
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="outline"
                onClick={() => downloadTemplate("inventory")}
                disabled={uploading}
                className="w-full gap-2"
              >
                <Download className="h-4 w-4" />
                {uploading ? "Downloading..." : "Download Template"}
              </Button>

              <ImportUploadArea
                tab={tab}
                fileToUpload={fileToUpload}
                onFileSelect={handleFileSelect}
                onImport={handleImport}
                importing={importing}
              />

              {importResult && <ImportResults result={importResult} type="inventory" />}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {errors.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-base text-red-900 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Import Errors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell className="text-red-900">Row</TableCell>
                    <TableCell className="text-red-900">Error</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {errors.slice(0, 50).map((err, idx) => (
                    <TableRow key={idx} className="border-red-200">
                      <TableCell className="text-xs font-mono text-red-700">{err.row}</TableCell>
                      <TableCell className="text-xs text-red-700">{err.error}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {errors.length > 50 && (
                <p className="mt-2 text-xs text-red-700">... and {errors.length - 50} more errors</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}

function ImportUploadArea({ tab, fileToUpload, onFileSelect, onImport, importing }) {
  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center hover:border-slate-400 hover:bg-slate-100 transition-colors">
        <input
          type="file"
          accept=".csv"
          onChange={onFileSelect}
          className="absolute inset-0 cursor-pointer opacity-0"
          data-testid={`import-file-input-${tab}`}
        />
        <div className="flex flex-col items-center gap-2">
          <FileUp className="h-10 w-10 text-slate-400" />
          <p className="font-medium text-slate-700">Drag and drop CSV file here or click to browse</p>
          <p className="text-xs text-slate-500">Only CSV files accepted</p>
        </div>
      </div>

      {fileToUpload && (
        <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-4">
          <div>
            <p className="font-medium text-green-900">{fileToUpload.name}</p>
            <p className="text-xs text-green-700">{(fileToUpload.size / 1024).toFixed(2)} KB</p>
          </div>
          <Button onClick={onImport} disabled={importing} size="sm" className="gap-2">
            <Upload className="h-4 w-4" />
            {importing ? "Importing..." : "Import"}
          </Button>
        </div>
      )}
    </div>
  );
}

function ImportResults({ result, type }) {
  const successCount = result.success_count || result.imported_count || 0;
  const hasErrors = result.errors && result.errors.length > 0;

  return (
    <Alert className={hasErrors ? "border-yellow-200 bg-yellow-50" : "border-green-200 bg-green-50"}>
      <CheckCircle className={hasErrors ? "text-yellow-600" : "text-green-600"} />
      <AlertDescription>
        <p className={hasErrors ? "text-yellow-900" : "text-green-900"}>
          {successCount} {type} {successCount === 1 ? "item" : "items"} imported successfully
        </p>
        {hasErrors && (
          <p className="text-xs text-yellow-700 mt-1">
            {result.errors.length} {result.errors.length === 1 ? "error" : "errors"} found during import
          </p>
        )}
      </AlertDescription>
    </Alert>
  );
}
