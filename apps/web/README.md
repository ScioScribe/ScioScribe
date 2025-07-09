# ScioScribe Web Application

ScioScribe is an AI-powered research co-pilot that helps you analyze data, create visualizations, and conduct experiments. This web application demonstrates the system's capabilities using the classic Iris flower dataset.

## Features

- **🌸 Iris Dataset Analysis**: Pre-loaded with 75 iris flower measurements across 3 species
- **📝 Interactive Text Editor**: Edit experiment plans with syntax highlighting
- **📊 Data Table Viewer**: View, search, and edit CSV data in real-time
- **📈 Visualization Engine**: Generate interactive Plotly charts using AI
- **🤖 AI Chat Interface**: Natural language interface for data analysis

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend server running on `localhost:8000` (see [server README](../../server/README.md))

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:5173](http://localhost:5173) in your browser

## Using the Application

### 1. Explore the Iris Dataset

The application comes pre-loaded with the famous Iris flower dataset containing:
- **sepal_length**: Length of flower sepal in cm
- **sepal_width**: Width of flower sepal in cm  
- **petal_length**: Length of flower petal in cm
- **petal_width**: Width of flower petal in cm
- **species**: Iris species (setosa, versicolor, virginica)

### 2. Data Table Features

- **Search**: Use the search box to filter data
- **Edit**: Click any cell to edit values
- **Download**: Export filtered data as CSV
- **View**: 75 total observations with real-time row counts

### 3. AI-Powered Analysis

Click the lightbulb icon (💡) in the AI chat to see suggested prompts:

#### Visualization Examples:
- "Create a scatter plot showing the relationship between sepal length and sepal width, colored by species"
- "Generate a box plot comparing petal lengths across different iris species"
- "Show a correlation heatmap of all numeric features in the iris dataset"

#### Analysis Examples:
- "Analyze the statistical differences between iris species"
- "Identify which features best distinguish between species"
- "What are the key characteristics that distinguish setosa from other species?"

### 4. Interactive Visualizations

Generated charts appear in the Visualization panel with:
- **Interactive Controls**: Zoom, pan, hover for details
- **Full Screen**: Click the maximize button
- **Responsive Design**: Auto-adjusts to panel size
- **Dark Mode Support**: Automatically adapts to theme

### 5. Experiment Planning

The text editor contains a pre-written experiment plan for iris analysis:
- **Research Questions**: Clear objectives for analysis
- **Methodology**: Step-by-step analysis approach
- **Expected Outcomes**: What insights to discover
- **Quality Checks**: Validation steps

## Sample Workflow

1. **Start with the Data**: Explore the iris dataset in the data table
2. **Review the Plan**: Read the experiment plan in the text editor
3. **Ask Questions**: Use the AI chat to generate visualizations
4. **Analyze Results**: Examine patterns in the generated charts
5. **Iterate**: Refine questions based on initial findings

## Technical Details

### Data Format

The application expects CSV data with headers. The iris dataset includes:
```csv
sepal_length,sepal_width,petal_length,petal_width,species
5.1,3.5,1.4,0.2,setosa
4.9,3.0,1.4,0.2,setosa
...
```

### API Integration

The frontend communicates with the backend analysis service via:
- **Endpoint**: `POST /api/analysis/generate-visualization`
- **Request**: JSON with prompt, plan, and CSV data
- **Response**: HTML containing interactive Plotly visualization

### Component Architecture

- `App.tsx`: Main application with state management
- `AiChat.tsx`: Natural language interface for analysis requests
- `DataTableViewer.tsx`: Interactive CSV data display and editing
- `GraphViewer.tsx`: Plotly visualization rendering with controls
- `TextEditor.tsx`: Experiment plan editing with line numbers

## Troubleshooting

### Common Issues

1. **No visualizations generated**:
   - Ensure backend server is running on localhost:8000
   - Check browser console for API errors
   - Try suggested prompts from the lightbulb icon

2. **Data not loading**:
   - Check that placeholder data is properly imported
   - Verify CSV format and headers

3. **Charts not displaying**:
   - Ensure iframe sandbox permissions are enabled
   - Check for JavaScript errors in browser console

### Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type checking
npm run type-check
```

## Next Steps

1. **Custom Data**: Replace iris dataset with your own CSV data
2. **New Analysis Types**: Extend AI prompts for different analysis types
3. **Enhanced Visualizations**: Add support for more chart types
4. **Export Features**: Save results and generated insights

## Contributing

See the main [README](../../README.md) for contribution guidelines.

## License

See [LICENSE](../../LICENSE) for details.
