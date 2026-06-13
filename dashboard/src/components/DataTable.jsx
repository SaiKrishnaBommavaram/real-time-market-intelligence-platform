import { useDeferredValue, useMemo, useState } from "react";

function defaultSortValue(row, column) {
  const value = column.accessor ? column.accessor(row) : row[column.key];
  return value ?? "";
}

export function DataTable({
  rows,
  columns,
  searchPlaceholder = "Filter rows",
  emptyMessage = "No rows available.",
  rowKey,
  initialSortKey,
  initialSortDirection = "desc",
  height = 420,
  rowHeight = 52,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const deferredSearchTerm = useDeferredValue(searchTerm);
  const [sortKey, setSortKey] = useState(initialSortKey || columns[0]?.key);
  const [sortDirection, setSortDirection] = useState(initialSortDirection);
  const [visibleColumnKeys, setVisibleColumnKeys] = useState(
    columns.map((column) => column.key),
  );
  const [scrollTop, setScrollTop] = useState(0);

  const visibleColumns = useMemo(
    () => columns.filter((column) => visibleColumnKeys.includes(column.key)),
    [columns, visibleColumnKeys],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();
    if (!normalizedSearch) {
      return rows;
    }

    return rows.filter((row) =>
      visibleColumns.some((column) => {
        const value = column.accessor ? column.accessor(row) : row[column.key];
        return String(value ?? "").toLowerCase().includes(normalizedSearch);
      }),
    );
  }, [deferredSearchTerm, rows, visibleColumns]);

  const sortedRows = useMemo(() => {
    const activeColumn = columns.find((column) => column.key === sortKey) || columns[0];
    if (!activeColumn) {
      return filteredRows;
    }

    return [...filteredRows].sort((left, right) => {
      const leftValue = defaultSortValue(left, activeColumn);
      const rightValue = defaultSortValue(right, activeColumn);

      if (typeof leftValue === "number" && typeof rightValue === "number") {
        return sortDirection === "asc" ? leftValue - rightValue : rightValue - leftValue;
      }

      return sortDirection === "asc"
        ? String(leftValue).localeCompare(String(rightValue))
        : String(rightValue).localeCompare(String(leftValue));
    });
  }, [columns, filteredRows, sortDirection, sortKey]);

  const totalHeight = sortedRows.length * rowHeight;
  const overscan = 6;
  const visibleCount = Math.max(Math.ceil(height / rowHeight) + overscan, 1);
  const startIndex = Math.max(Math.floor(scrollTop / rowHeight) - 2, 0);
  const visibleRows = sortedRows.slice(startIndex, startIndex + visibleCount);
  const topSpacerHeight = startIndex * rowHeight;

  function toggleSort(nextKey) {
    if (nextKey === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortKey(nextKey);
    setSortDirection("desc");
  }

  function toggleColumn(columnKey) {
    setVisibleColumnKeys((currentKeys) => {
      if (currentKeys.includes(columnKey)) {
        if (currentKeys.length === 1) {
          return currentKeys;
        }
        return currentKeys.filter((key) => key !== columnKey);
      }

      return [...currentKeys, columnKey];
    });
  }

  return (
    <div className="data-table-shell">
      <div className="data-table-toolbar">
        <input
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder={searchPlaceholder}
        />

        <div className="column-toggle-list">
          {columns.map((column) => (
            <label key={column.key} className="column-toggle">
              <input
                type="checkbox"
                checked={visibleColumnKeys.includes(column.key)}
                onChange={() => toggleColumn(column.key)}
              />
              <span>{column.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="data-table">
        <div
          className="data-table-header"
          style={{ gridTemplateColumns: `repeat(${visibleColumns.length}, minmax(0, 1fr))` }}
        >
          {visibleColumns.map((column) => (
            <button
              key={column.key}
              className="data-table-sort"
              onClick={() => toggleSort(column.key)}
            >
              <span>{column.label}</span>
              <span className="sort-indicator">
                {sortKey === column.key ? (sortDirection === "asc" ? "↑" : "↓") : "·"}
              </span>
            </button>
          ))}
        </div>

        {!sortedRows.length ? (
          <div className="empty table-empty">{emptyMessage}</div>
        ) : (
          <div
            className="data-table-viewport"
            style={{ height }}
            onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
          >
            <div style={{ height: totalHeight, position: "relative" }}>
              <div
                style={{
                  position: "absolute",
                  top: topSpacerHeight,
                  left: 0,
                  right: 0,
                  display: "grid",
                  gap: 8,
                }}
              >
                {visibleRows.map((row, index) => (
                  <div
                    key={rowKey ? rowKey(row) : `${startIndex + index}`}
                    className="data-table-row"
                    style={{
                      minHeight: rowHeight,
                      gridTemplateColumns: `repeat(${visibleColumns.length}, minmax(0, 1fr))`,
                    }}
                  >
                    {visibleColumns.map((column) => (
                      <div key={column.key} className="data-table-cell">
                        {column.render ? column.render(row) : String(defaultSortValue(row, column))}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
