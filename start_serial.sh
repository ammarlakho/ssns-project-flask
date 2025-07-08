#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📡 Starting Serial to HTTP Bridge${NC}"
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
echo -e "${YELLOW}🔍 Checking serial dependencies...${NC}"
missing_deps=()

if ! python -c "import serial" &> /dev/null; then
    missing_deps+=("pyserial")
fi

if ! python -c "import requests" &> /dev/null; then
    missing_deps+=("requests")
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${YELLOW}📥 Installing missing dependencies: ${missing_deps[*]}...${NC}"
    pip install "${missing_deps[@]}"
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo -e "${GREEN}✅ All dependencies already installed${NC}"
fi

# Check if serial_to_http.py exists
if [ ! -f "serial_to_http.py" ]; then
    echo -e "${RED}❌ serial_to_http.py not found!${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo -e "${GREEN}✅ All checks passed!${NC}"
echo ""
echo -e "${BLUE}📡 Starting Serial to HTTP bridge...${NC}"
echo -e "${YELLOW}🔌 Serial Configuration:${NC}"
echo -e "   ${GREEN}Port: /dev/tty.usbmodem0010502681671${NC}"
echo -e "   ${GREEN}Baud Rate: 115200${NC}"
echo ""
echo -e "${YELLOW}🌐 Target Server:${NC}"
echo -e "   ${GREEN}http://localhost:8000/api/readings${NC}"
echo ""
echo -e "${YELLOW}📋 Data Format Expected:${NC}"
echo -e "   ${GREEN}<DATA>co2,temp,humidity,vocs,pm25,pm10</DATA>${NC}"
echo ""
echo -e "${YELLOW}📝 Logs will be written to:${NC}"
echo -e "   ${GREEN}logs/serial.log${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the bridge${NC}"
echo ""

# Function to handle graceful shutdown
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down Serial to HTTP bridge...${NC}"
    if [ ! -z "$SERIAL_PID" ]; then
        kill $SERIAL_PID 2>/dev/null
        wait $SERIAL_PID 2>/dev/null
    fi
    echo -e "${GREEN}✅ Serial bridge stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run the Serial to HTTP bridge with enhanced logging
python serial_to_http.py 2>&1 | tee logs/serial.log &
SERIAL_PID=$!

# Wait for the process
wait $SERIAL_PID 