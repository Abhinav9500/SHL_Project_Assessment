import streamlit as st
import time
from vector_engine import get_recommendations

# --- Page Configuration ---
st.set_page_config(
    page_title="SHL Assessment Recommender",
    page_icon="##",
    layout="centered"
)

# --- Custom CSS for Styling ---
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Input label and general text */
    .stMarkdown, p, h1, h2, h3, h4, label {
        color: #ffffff !important;
    }

    /* Input text box */
    .stTextInput>div>div>input {
        background-color: #1e1e1e;
        color: #ffffff;
        border: 1px solid #4CAF50;
    }

    /* Button styling */
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        height: 50px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #45a049;
        color: white;
    }

    /* Result box styling */
    .recommendation-box {
        background-color: #1e1e1e;
        padding: 25px;
        border-radius: 12px;
        border-left: 5px solid #4CAF50;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
        margin-top: 20px;
        color: #ffffff;
        line-height: 1.6;
    }

    /* Table styling for dark mode */
    .stTable {
        background-color: #1e1e1e;
        color: #ffffff;
        border-radius: 10px;
    }
    thead tr th {
        background-color: #333333 !important;
        color: #4CAF50 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Header Section ---
st.title("SHL Smart Assessment Recommender")
st.markdown("Enter a job role or skill requirement below, and our AI will recommend the best assessments from the SHL catalog.")

# --- Input Section ---
query = st.text_input("What role are you hiring for?", placeholder="e.g., Senior Java Developer, Accountant, Sales Manager...")

# --- Logic ---
if st.button("Find Assessments"):
    if query:
        with st.spinner(" Searching catalog and generating AI insights..."):
            # Call the backend function we built
            try:
                result = get_recommendations(query)
                
                # Display Results
                st.subheader(" AI Recommendation")
                st.markdown(f"""
                <div class="recommendation-box">
                    {result.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a job role to search.")

# --- Footer ---
st.markdown("---")
st.caption("Powered by Google Gemini & ChromaDB | Developed by Abhinav Jain MTech (AI), IIIT Vadodara | 2025")