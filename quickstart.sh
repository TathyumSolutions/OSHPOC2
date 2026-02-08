#!/bin/bash

# Insurance Eligibility Agent - Quick Start Script
# This script helps set up and run the entire application

echo "========================================="
echo "Insurance Eligibility Agent Setup"
echo "========================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo "✓ Python version: $python_version"

# Check if OpenAI API key is set
if [ -f "backend/.env" ]; then
    if grep -q "your-openai-api-key-here" backend/.env; then
        echo "⚠️  WARNING: OpenAI API key not set in backend/.env"
        echo "   Please edit backend/.env and add your OpenAI API key"
        echo ""
    else
        echo "✓ OpenAI API key configured"
    fi
else
    echo "⚠️  Creating backend/.env from template..."
    cp backend/.env.example backend/.env
    echo "   Please edit backend/.env and add your OpenAI API key"
    echo ""
fi

# Function to setup backend
setup_backend() {
    echo "Setting up Backend..."
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "  Installing dependencies..."
    pip install -q -r requirements.txt
    
    echo "✓ Backend setup complete"
    cd ..
}

# Function to setup frontend
setup_frontend() {
    echo "Setting up Frontend..."
    cd frontend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "  Installing dependencies..."
    pip install -q -r requirements.txt
    
    echo "✓ Frontend setup complete"
    cd ..
}

# Function to run backend
run_backend() {
    echo ""
    echo "Starting Backend API..."
    cd backend
    source venv/bin/activate
    python app.py
}

# Function to run frontend
run_frontend() {
    echo ""
    echo "Starting Frontend..."
    cd frontend
    source venv/bin/activate
    streamlit run streamlit_app.py
}

# Main menu
echo ""
echo "What would you like to do?"
echo "1. Setup (Install dependencies)"
echo "2. Run Backend API"
echo "3. Run Frontend"
echo "4. Setup and Run Everything"
echo "5. Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        setup_backend
        setup_frontend
        echo ""
        echo "✓ Setup complete!"
        echo "  Run 'bash quickstart.sh' and choose option 2 & 3 to start"
        ;;
    2)
        run_backend
        ;;
    3)
        run_frontend
        ;;
    4)
        setup_backend
        setup_frontend
        echo ""
        echo "✓ Setup complete!"
        echo ""
        echo "Starting services..."
        echo "  Backend will run in this terminal"
        echo "  Open a new terminal and run: cd frontend && source venv/bin/activate && streamlit run streamlit_app.py"
        echo ""
        run_backend
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
