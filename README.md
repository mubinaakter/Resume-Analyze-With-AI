# Resume Analyzer

Resume Analyzer is an intelligent tool that uses natural language processing to extract information from resumes and identify important keywords. It then groups these keywords into relevant sectors and provides personalized recommendations, predictions, and insights for the applicant based on keyword matching.

This project aims to help job seekers understand how their resumes align with targeted sectors, improve their resumes with actionable recommendations, and visualize analytics for better career planning.

---

## ✨ Features

- Parse and extract structured data (name, email, phone, education, skills, etc.) from resumes (PDF/DOCX).
- Identify and highlight important keywords automatically.
- Cluster keywords into relevant sectors for clear visualization.
- Provide personalized recommendations for resume improvement.
- Predict applicant fit based on keyword and sector matching.
- Display resume analytics and keyword insights.
- Simple, user-friendly Streamlit interface for upload and analysis.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **NLP Libraries:** `nltk`, `spacy`, `pyresparser`
- **PDF Parsing:** `pdfminer3`
- **Database:** MySQL
- **Deployment:** Streamlit Cloud / Local

---

## 🚀 Installation

1️⃣ Clone this repository:

```bash
git clone https://github.com/yourusername/resume-analyzer.git


2️⃣ Navigate into the project directory:

```bash
cd resume-analyzer


3️⃣ Install all required dependencies:

```bash
pip install -r requirements.txt


4️⃣ Run the Streamlit app locally:

```bash
streamlit run app.py


## 📈 Usage

1️⃣ Upload your resume (PDF/DOCX).
2️⃣ View extracted data and keyword clusters.
3️⃣ See recommendations for improving your resume.
4️⃣ Check analytics and keyword matching with sectors.
5️⃣ Refine your resume based on insights provided.

## 📂 Project Structure

resume-analyzer/
├── app.py
├── utils/
│   ├── parser.py
│   ├── analyzer.py
│   └── recommender.py
├── requirements.txt
└── README.md
