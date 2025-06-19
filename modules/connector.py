import streamlit as st
from streamlit_gsheets import GSheetsConnection

conn = st.connection("gsheets", type=GSheetsConnection)

class Connection:
    def __init__(self, gid):
        self.url = f"https://docs.google.com/spreadsheets/d/1Iap_cFdzJ201bkMpy5_kuRFEkxi8eEk1yRoi2et_IHo/edit?gid={gid}"
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def get_connection(self):
        return self.conn

    def get_url(self):
        return self.url
