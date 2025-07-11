"use client"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BarChart3, RefreshCw, Maximize2 } from "lucide-react"

interface GraphViewerProps {
  htmlContent?: string
  onRefresh?: () => void
}

export function GraphViewer({ htmlContent, onRefresh }: GraphViewerProps) {
  const [currentHtml, setCurrentHtml] = useState("")
  const [isFullscreen, setIsFullscreen] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Enhanced Plotly HTML content specifically for iris dataset
  const irisPlaceholderHTML = `
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
            height: 100%; 
            width: 100%; 
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <div id="plotly-div"></div>
    <script>
        // Sample iris data for placeholder visualization
        const setosaX = [5.1, 4.9, 4.7, 4.6, 5.0, 5.4, 4.6, 5.0, 4.4, 4.9];
        const setosaY = [3.5, 3.0, 3.2, 3.1, 3.6, 3.9, 3.4, 3.4, 2.9, 3.1];
        
        const versicolorX = [7.0, 6.4, 6.9, 5.5, 6.5, 5.7, 6.3, 4.9, 6.6, 5.2];
        const versicolorY = [3.2, 3.2, 3.1, 2.3, 2.8, 2.8, 3.3, 2.4, 2.9, 2.7];
        
        const virginicaX = [6.3, 5.8, 7.1, 6.3, 6.5, 7.6, 4.9, 7.3, 6.7, 7.2];
        const virginicaY = [3.3, 2.7, 3.0, 2.9, 3.0, 3.0, 2.5, 2.9, 2.5, 3.6];
        
        const data = [
            {
                x: setosaX,
                y: setosaY,
                mode: 'markers',
                type: 'scatter',
                name: 'Setosa',
                marker: { 
                    color: '#ff6b6b', 
                    size: 8,
                    symbol: 'circle'
                }
            },
            {
                x: versicolorX,
                y: versicolorY,
                mode: 'markers',
                type: 'scatter',
                name: 'Versicolor',
                marker: { 
                    color: '#4ecdc4', 
                    size: 8,
                    symbol: 'diamond'
                }
            },
            {
                x: virginicaX,
                y: virginicaY,
                mode: 'markers',
                type: 'scatter',
                name: 'Virginica',
                marker: { 
                    color: '#45b7d1', 
                    size: 8,
                    symbol: 'square'
                }
            }
        ];
        
        const layout = {
            title: {
                text: 'Iris Dataset: Sepal Length vs Width by Species',
                font: { size: 14, color: '#6b7280' },
                x: 0.5
            },
            xaxis: { 
                title: 'Sepal Length (cm)',
                gridcolor: '#374151',
                linecolor: '#374151',
                tickcolor: '#374151',
                tickfont: { size: 10, color: '#6b7280' },
                titlefont: { size: 11, color: '#6b7280' }
            },
            yaxis: { 
                title: 'Sepal Width (cm)',
                gridcolor: '#374151',
                linecolor: '#374151',
                tickcolor: '#374151',
                tickfont: { size: 10, color: '#6b7280' },
                titlefont: { size: 11, color: '#6b7280' }
            },
            legend: {
                font: { size: 10, color: '#6b7280' },
                x: 1,
                y: 1,
                bgcolor: 'rgba(255,255,255,0.8)',
                bordercolor: '#374151',
                borderwidth: 1
            },
            margin: { l: 60, r: 40, t: 50, b: 50 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { 
                family: 'ui-monospace, monospace', 
                size: 10,
                color: '#6b7280'
            },
            showlegend: true,
            autosize: true
        };
        
        const config = {
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d'],
            responsive: true,
            autosizable: true,
            displaylogo: false
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
        
        // Listen for resize messages from parent
        window.addEventListener('message', function(event) {
            if (event.data.type === 'resize') {
                setTimeout(() => {
                    Plotly.Plots.resize('plotly-div');
                }, 100);
            }
        });
        
        // Handle dark mode
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            Plotly.relayout('plotly-div', {
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'font.color': '#9ca3af',
                'title.font.color': '#9ca3af',
                'xaxis.gridcolor': '#4b5563',
                'yaxis.gridcolor': '#4b5563',
                'xaxis.linecolor': '#4b5563',
                'yaxis.linecolor': '#4b5563',
                'xaxis.tickcolor': '#4b5563',
                'yaxis.tickcolor': '#4b5563',
                'xaxis.tickfont.color': '#9ca3af',
                'yaxis.tickfont.color': '#9ca3af',
                'xaxis.titlefont.color': '#9ca3af',
                'yaxis.titlefont.color': '#9ca3af',
                'legend.bgcolor': 'rgba(17,24,39,0.8)',
                'legend.bordercolor': '#4b5563',
                'legend.font.color': '#9ca3af'
            });
        }
    </script>
</body>
</html>`

  useEffect(() => {
    if (htmlContent && htmlContent.trim() !== "") {
      setCurrentHtml(htmlContent)
    } else {
      setCurrentHtml(irisPlaceholderHTML)
    }
  }, [htmlContent, irisPlaceholderHTML])

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      if (containerRef.current?.requestFullscreen) {
        containerRef.current.requestFullscreen()
        setIsFullscreen(true)
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
        setIsFullscreen(false)
      }
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // Handle iframe resizing
  useEffect(() => {
    const iframe = iframeRef.current
    const container = containerRef.current
    
    if (!iframe || !container) return

    const resizeObserver = new ResizeObserver(() => {
      // Send resize message to iframe content
      iframe.contentWindow?.postMessage({ type: 'resize' }, '*')
    })

    resizeObserver.observe(container)

    return () => {
      resizeObserver.disconnect()
    }
  }, [currentHtml])

  return (
    <Card 
      ref={containerRef}
      className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800 w-full"
    >
      <CardHeader className="flex-shrink-0 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2 dark:text-white">
            <BarChart3 className="h-4 w-4" />
            Visualization
            {htmlContent && (
              <span className="text-xs text-green-600 dark:text-green-400">
                • Live
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-1">
            {onRefresh && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={onRefresh}
              >
                <RefreshCw className="h-3 w-3" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={toggleFullscreen}
            >
              <Maximize2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <div className="flex-1 min-h-0 border-t dark:border-gray-700 overflow-hidden">
          {currentHtml ? (
            <iframe
              ref={iframeRef}
              srcDoc={currentHtml}
              className="w-full h-full border-0"
              style={{
                background: "transparent",
                colorScheme: "dark",
                minHeight: "0",
                minWidth: "0",
              }}
              sandbox="allow-scripts allow-same-origin"
              title="Data Visualization"
            />
          ) : (
            <div className="flex items-center justify-center h-full text-xs text-muted-foreground dark:text-gray-400">
              <div className="text-center">
                <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No visualization available</p>
                <p className="text-xs mt-1 opacity-75">Use the AI chat to generate charts</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
