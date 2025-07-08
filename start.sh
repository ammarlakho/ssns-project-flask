#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Flask Application${NC}"
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo -e "${YELLOW}Please run setup first:${NC}"
    echo -e "   ${GREEN}./setup.sh${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Check if dependencies are installed using the virtual environment's Python
if ! python -c "import flask" &> /dev/null; then
    echo -e "${YELLOW}📥 Installing dependencies...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ app.py not found!${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo -e "${GREEN}✅ All checks passed!${NC}"
echo ""
echo -e "${BLUE}🌐 Starting Flask development server...${NC}"
echo -e "${YELLOW}📱 The application will be available at:${NC}"
echo -e "   ${GREEN}http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}🔌 API endpoints:${NC}"
echo -e "   ${GREEN}http://localhost:8000/api/health${NC}"
echo -e "   ${GREEN}http://localhost:8000/api/readings/current${NC}"
echo -e "   ${GREEN}http://localhost:8000//api/readings${NC}"
echo -e "   ${GREEN}http://localhost:8000/api/parameters${NC}"
echo ""
echo -e "${YELLOW}📝 Logs will be written to:${NC}"
echo -e "   ${GREEN}app.log${NC}"
echo -e "   ${GREEN}logs/flask.log${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Function to handle graceful shutdown
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down Flask application...${NC}"
    if [ ! -z "$FLASK_PID" ]; then
        kill $FLASK_PID 2>/dev/null
        wait $FLASK_PID 2>/dev/null
    fi
    echo -e "${GREEN}✅ Flask application stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run the Flask application with enhanced logging
python app.py 2>&1 | tee logs/flask.log &
FLASK_PID=$!

# Wait for the process
wait $FLASK_PID 