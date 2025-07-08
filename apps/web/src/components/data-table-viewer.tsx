import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Upload } from "lucide-react"

interface TableData {
  id: string
  name: string
  value: string
  status: string
}

export function DataTableViewer() {
  const [data, setData] = useState<TableData[]>([
    { id: "1", name: "Revenue Target", value: "45200", status: "active" },
    { id: "2", name: "User Growth", value: "2350", status: "pending" },
    { id: "3", name: "Conversion Rate", value: "3.2", status: "active" },
    { id: "4", name: "Monthly Goal", value: "68", status: "active" },
    { id: "5", name: "Support Tickets", value: "12", status: "pending" },
  ])

  const handleCellEdit = (id: string, field: keyof TableData, value: string) => {
    setData((prev) => prev.map((row) => (row.id === id ? { ...row, [field]: value } : row)))
  }

  const handleUpload = () => {
    // Simulate file upload
    console.log("Upload functionality would be implemented here")
  }

  return (
    <Card className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800">
      <CardHeader className="flex-shrink-0 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base dark:text-white">Data</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs px-2 dark:text-gray-300 dark:hover:text-white"
            onClick={handleUpload}
          >
            <Upload className="h-3 w-3 mr-1" />
            Upload
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <div className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-b dark:border-gray-700">
                <TableHead
                  className="text-xs font-medium h-8 px-4 dark:text-gray-400"
                  style={{
                    fontFamily:
                      'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                  }}
                >
                  name
                </TableHead>
                <TableHead
                  className="text-xs font-medium h-8 px-4 dark:text-gray-400"
                  style={{
                    fontFamily:
                      'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                  }}
                >
                  value
                </TableHead>
                <TableHead
                  className="text-xs font-medium h-8 px-4 dark:text-gray-400"
                  style={{
                    fontFamily:
                      'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                  }}
                >
                  status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((row) => (
                <TableRow
                  key={row.id}
                  className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <TableCell className="py-2 px-4">
                    <Input
                      value={row.name}
                      onChange={(e) => handleCellEdit(row.id, "name", e.target.value)}
                      className="border-0 bg-transparent p-0 h-auto text-xs dark:text-gray-100 focus-visible:ring-0"
                      style={{
                        fontFamily:
                          'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                      }}
                    />
                  </TableCell>
                  <TableCell className="py-2 px-4">
                    <Input
                      value={row.value}
                      onChange={(e) => handleCellEdit(row.id, "value", e.target.value)}
                      className="border-0 bg-transparent p-0 h-auto text-xs dark:text-gray-100 focus-visible:ring-0"
                      style={{
                        fontFamily:
                          'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                      }}
                    />
                  </TableCell>
                  <TableCell className="py-2 px-4">
                    <Input
                      value={row.status}
                      onChange={(e) => handleCellEdit(row.id, "status", e.target.value)}
                      className="border-0 bg-transparent p-0 h-auto text-xs dark:text-gray-100 focus-visible:ring-0"
                      style={{
                        fontFamily:
                          'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                      }}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
