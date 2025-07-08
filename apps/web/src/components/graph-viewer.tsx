"use client"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart3 } from "lucide-react"

export function GraphViewer() {
  const [htmlContent, setHtmlContent] = useState("")
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Placeholder Plotly HTML content with better sizing
  const placeholderPlotlyHTML = `
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        html, body { 
            margin: 0; 
            padding: 0; 
            height: 100%; 
            width: 100%; 
            background: transparent; 
            font-family: ui-monospace, monospace;
            overflow: hidden;
        }
        #plotly-div { 
            height: 100vh; 
            width: 100vw; 
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <div id="plotly-div"></div>
    <script>
        const data = [{
            x: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            y: [20, 35, 30, 45, 55, 48],
            type: 'scatter',
            mode: 'lines+markers',
            marker: { color: '#3b82f6', size: 4 },
            line: { color: '#3b82f6', width: 2 }
        }];
        
        const layout = {
            margin: { l: 25, r: 15, t: 15, b: 25 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { 
                family: 'ui-monospace, monospace', 
                size: 9,
                color: '#6b7280'
            },
            xaxis: { 
                gridcolor: '#374151',
                linecolor: '#374151',
                tickcolor: '#374151',
                tickfont: { size: 8 }
            },
            yaxis: { 
                gridcolor: '#374151',
                linecolor: '#374151',
                tickcolor: '#374151',
                tickfont: { size: 8 }
            },
            showlegend: false,
            autosize: true
        };
        
        const config = {
            displayModeBar: false,
            responsive: true,
            autosizable: true
        };
        
        function createPlot() {
            Plotly.newPlot('plotly-div', data, layout, config);
        }
        
        // Initial plot
        createPlot();
        
        // Handle window resize
        window.addEventListener('resize', function() {
            Plotly.Plots.resize('plotly-div');
        });
        
        // Handle dark mode
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            Plotly.relayout('plotly-div', {
                'font.color': '#9ca3af',
                'font.size': 9,
                'xaxis.gridcolor': '#4b5563',
                'yaxis.gridcolor': '#4b5563',
                'xaxis.linecolor': '#4b5563',
                'yaxis.linecolor': '#4b5563',
                'xaxis.tickcolor': '#4b5563',
                'yaxis.tickcolor': '#4b5563',
                'xaxis.tickfont.size': 8,
                'yaxis.tickfont.size': 8
            });
        }
    </script>
</body>
</html>`

  useEffect(() => {
    setHtmlContent(placeholderPlotlyHTML)
  }, [])

  return (
    <Card className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800">
      <CardHeader className="flex-shrink-0 pb-2">
        <CardTitle className="text-base flex items-center gap-2 dark:text-white">
          <BarChart3 className="h-4 w-4" />
          Graph
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <div className="flex-1 min-h-0 border-t dark:border-gray-700 overflow-hidden">
          {htmlContent ? (
            <iframe
              ref={iframeRef}
              srcDoc={htmlContent}
              className="w-full h-full border-0"
              style={{
                background: "transparent",
                colorScheme: "dark",
                minHeight: "0",
                minWidth: "0",
              }}
              sandbox="allow-scripts allow-same-origin"
              title="Plotly Graph"
            />
          ) : (
            <div className="flex items-center justify-center h-full text-xs text-muted-foreground dark:text-gray-400">
              <div className="text-center">
                <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>Upload Plotly HTML to view graph</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
