import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  Download,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Columns3,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: string;
  accessor: (row: T) => React.ReactNode;
  sortable?: boolean;
  searchable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyField: keyof T;
  searchPlaceholder?: string;
  pageSize?: number;
  bulkActions?: { label: string; icon?: React.ReactNode; onClick: (selected: T[]) => void; variant?: "default" | "destructive" }[];
  emptyMessage?: string;
  isLoading?: boolean;
  renderRowActions?: (row: T) => React.ReactNode;
}

type SortDir = "asc" | "desc" | null;

export function DataTable<T>({
  data,
  columns,
  keyField,
  searchPlaceholder = "Search...",
  pageSize = 10,
  bulkActions,
  emptyMessage = "No data to display.",
  isLoading = false,
  renderRowActions,
}: DataTableProps<T>) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [page, setPage] = useState(0);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set(columns.map((c) => c.key)));
  const [showColumnPicker, setShowColumnPicker] = useState(false);

  const searchableKeys = useMemo(() => columns.filter((c) => c.searchable !== false).map((c) => c.key), [columns]);

  const filteredData = useMemo(() => {
    if (!search.trim()) return data;
    const lower = search.toLowerCase();
    return data.filter((row) =>
      searchableKeys.some((key) => {
        const val = (row as any)[key];
        return val != null && String(val).toLowerCase().includes(lower);
      }),
    );
  }, [data, search, searchableKeys]);

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = (a as any)[sortKey];
      const bVal = (b as any)[sortKey];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = typeof aVal === "string" ? aVal.localeCompare(bVal) : aVal < bVal ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filteredData, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));
  const pagedData = sortedData.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : d === "desc" ? null : "asc"));
      if (sortDir === "desc") setSortKey(null);
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(0);
  };

  const toggleSelectAll = () => {
    if (selectedKeys.size === pagedData.length) {
      setSelectedKeys(new Set());
    } else {
      setSelectedKeys(new Set(pagedData.map((r) => String(r[keyField]))));
    }
  };

  const toggleSelect = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const selectedRows = useMemo(
    () => pagedData.filter((r) => selectedKeys.has(String(r[keyField]))),
    [pagedData, selectedKeys, keyField],
  );

  const handleExportCSV = useCallback(() => {
    const headers = columns.filter((c) => visibleColumns.has(c.key)).map((c) => c.header);
    const rows = sortedData.map((row) =>
      columns
        .filter((c) => visibleColumns.has(c.key))
        .map((c) => {
          const val = (row as any)[c.key];
          return val != null ? String(val) : "";
        })
        .join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "export.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, [columns, sortedData, visibleColumns]);

  const toggleColumnVisibility = (key: string) => {
    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder={searchPlaceholder}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          {selectedKeys.size > 0 && bulkActions && (
            <div className="flex items-center gap-2 mr-2">
              <Badge variant="info">{selectedKeys.size} selected</Badge>
              {bulkActions.map((action) => (
                <Button
                  key={action.label}
                  variant={action.variant === "destructive" ? "destructive" : "outline"}
                  size="sm"
                  onClick={() => action.onClick(selectedRows)}
                >
                  {action.icon}
                  {action.label}
                </Button>
              ))}
            </div>
          )}
          <Button variant="outline" size="sm" onClick={handleExportCSV}>
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Export
          </Button>
          <div className="relative">
            <Button variant="outline" size="sm" onClick={() => setShowColumnPicker(!showColumnPicker)}>
              <Columns3 className="mr-1.5 h-3.5 w-3.5" />
              Columns
            </Button>
            <AnimatePresence>
              {showColumnPicker && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="absolute right-0 top-full mt-1 z-50 w-48 rounded-xl border border-border/70 bg-card p-2 shadow-lg"
                >
                  {columns.map((col) => (
                    <label key={col.key} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-muted/50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={visibleColumns.has(col.key)}
                        onChange={() => toggleColumnVisibility(col.key)}
                        className="rounded border-border"
                      />
                      {col.header}
                    </label>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-border/70">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="bg-muted/50">
              <tr>
                {bulkActions && (
                  <th className="w-10 px-3 py-3">
                    <input
                      type="checkbox"
                      checked={pagedData.length > 0 && selectedKeys.size === pagedData.length}
                      onChange={toggleSelectAll}
                      className="rounded border-border"
                    />
                  </th>
                )}
                {columns
                  .filter((c) => visibleColumns.has(c.key))
                  .map((col) => (
                    <th
                      key={col.key}
                      className={cn(
                        "px-4 py-3 text-left font-medium text-muted-foreground select-none",
                        col.sortable !== false && "cursor-pointer hover:text-foreground transition-colors",
                        col.className,
                      )}
                      onClick={() => col.sortable !== false && handleSort(col.key)}
                    >
                      <div className="flex items-center gap-1.5">
                        {col.header}
                        {col.sortable !== false && (
                          <span className="text-muted-foreground/60">
                            {sortKey === col.key && sortDir === "asc" ? (
                              <ArrowUp className="h-3.5 w-3.5 text-primary" />
                            ) : sortKey === col.key && sortDir === "desc" ? (
                              <ArrowDown className="h-3.5 w-3.5 text-primary" />
                            ) : (
                              <ArrowUpDown className="h-3.5 w-3.5" />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                {renderRowActions && <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-background/50">
              {isLoading && (
                <tr>
                  <td colSpan={columns.filter((c) => visibleColumns.has(c.key)).length + (bulkActions ? 1 : 0) + (renderRowActions ? 1 : 0)} className="px-4 py-8 text-center text-muted-foreground">
                    Loading...
                  </td>
                </tr>
              )}
              {!isLoading && pagedData.length === 0 && (
                <tr>
                  <td colSpan={columns.filter((c) => visibleColumns.has(c.key)).length + (bulkActions ? 1 : 0) + (renderRowActions ? 1 : 0)} className="px-4 py-8 text-center text-muted-foreground">
                    {emptyMessage}
                  </td>
                </tr>
              )}
              {!isLoading &&
                pagedData.map((row) => {
                  const rowKey = String(row[keyField]);
                  const isSelected = selectedKeys.has(rowKey);
                  return (
                    <tr
                      key={rowKey}
                      className={cn(
                        "transition-colors hover:bg-muted/30",
                        isSelected && "bg-primary/5",
                      )}
                    >
                      {bulkActions && (
                        <td className="w-10 px-3 py-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelect(rowKey)}
                            className="rounded border-border"
                          />
                        </td>
                      )}
                      {columns
                        .filter((c) => visibleColumns.has(c.key))
                        .map((col) => (
                          <td key={col.key} className={cn("px-4 py-3", col.className)}>
                            {col.accessor(row)}
                          </td>
                        ))}
                      {renderRowActions && (
                        <td className="px-4 py-3 text-right">{renderRowActions(row)}</td>
                      )}
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sortedData.length)} of {sortedData.length}
        </p>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" disabled={page === 0} onClick={() => setPage(0)}>
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="px-3 text-sm font-medium">
            {page + 1} / {totalPages}
          </span>
          <Button variant="outline" size="icon" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" disabled={page >= totalPages - 1} onClick={() => setPage(totalPages - 1)}>
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
