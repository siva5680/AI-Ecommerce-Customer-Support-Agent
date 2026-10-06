🛒 AI E-commerce Customer Support Agent

An AI-powered E-commerce Customer Support Agent built with Python and Streamlit. The application provides a user-friendly interface for handling customer support queries and interacting with e-commerce data.

🚀 Features

💬 AI-powered customer support interface

🛍️ E-commerce product and customer data management

🔎 Search and retrieve e-commerce information

📦 SQLite database integration

🖥️ Interactive Streamlit web interface

⚡ Fast and simple local deployment

🤖 Designed to assist customers with common e-commerce queries

🛠️ Technologies Used

Python

Streamlit

SQLite

AI / LLM Integration

Git & GitHub

📁 Project Structure
AI-Ecommerce-Customer-Support-Agent/
│
├── app.py
├── ecommerce.db
├── README.md
└── .gitignore

⚙️ Installation
1. Clone the repository
git clone https://github.com/siva5680/AI-Ecommerce-Customer-Support-Agent.git

2. Navigate to the project directory
cd AI-Ecommerce-Customer-Support-Agent

3. Create a virtual environment

Windows:

python -m venv venv


Activate it:

venv\Scripts\activate

4. Install dependencies

If a requirements.txt file is available:

pip install -r requirements.txt


Otherwise, install Streamlit:

pip install streamlit


Install any additional Python packages required by app.py.

▶️ Run the Application

Start the Streamlit application:

streamlit run app.py


The application will normally be available at:

http://localhost:8501

🗄️ Database

The project uses SQLite for storing e-commerce-related data.

The database file is:

ecommerce.db


⚠️ Do not commit sensitive customer information, passwords, API keys, or other private data to GitHub.

📸 Application

After starting the application, open:

http://localhost:8501


You can interact with the AI E-commerce Customer Support Agent through the Streamlit interface.

🔐 Environment Variables

If your application uses API keys or other credentials, store them in environment variables or Streamlit secrets rather than directly inside app.py.

For example:

OPENAI_API_KEY=your_api_key_here


Never upload real API keys to GitHub.

🤝 Contributing

Contributions are welcome!

Fork the repository

Create a new branch

git checkout -b feature/new-feature


Make your changes

Commit your changes

git add .
git commit -m "Add new feature"


Push the branch

git push origin feature/new-feature


Open a Pull Request

📄 License

This project is currently available for educational and development purposes.

👨‍💻 Author

Siva

GitHub: https://github.com/siva5680
