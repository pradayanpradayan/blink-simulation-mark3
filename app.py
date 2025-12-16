import streamlit as st
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import requests
import json
import serial
import threading
from datetime import datetime

# -------------------------------
# 🖌 Page Config & Custom Fonts
# -------------------------------
st.set_page_config(page_title="Blink Glucose Simulation", layout="wide")

st.markdown(
    """
    <style>
    /* Import font dari Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Roboto&display=swap');

    /* -------------------------------
       Background & Font Utama
    ------------------------------- */
    html, body, .stApp {
        font-family: 'Roboto', sans-serif !important;
        background-color: #f8f9fa !important; /* putih keabu */
        color: #222 !important;
    }

    /* -------------------------------
       Sidebar Styling
    ------------------------------- */
    [data-testid="stSidebar"] {
        background-color: #ac0000 !important; /* merah Blink */
        color: white !important;
    }

    [data-testid="stSidebar"] h2 {
        font-family: 'Archivo Black', sans-serif !important;
        color: #fff !important;
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #fff !important;
    }

    /* -------------------------------
       Judul
    ------------------------------- */
    h1, .css-10trblm h1, .css-1v3fvcr h1 {
        font-family: 'Archivo Black', sans-serif !important;
        color: #3a3a3a !important;
        text-align: center;
    }

    /* -------------------------------
       Glucose Metric Text
    ------------------------------- */
    .glucose-metric {
        font-family: 'Roboto', sans-serif !important;
        font-size: 17px !important;
        color: #d62828 !important;
        text-align: center;
        font-weight: 600;
    }

     /* === Tombol utama (Start / Stop Simulation) === */
    button[kind="primary"], div[data-testid="stButton"] button {
        background-color: #ac0000 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out;
    }

    button[kind="primary"]:hover, div[data-testid="stButton"] button:hover {
        background-color: #8a0000 !important;
        color: white !important;
    }

    /* === Tombol Simulation Duration (jika pakai st.selectbox atau st.radio) === */
    div[data-baseweb="select"] > div, div[data-baseweb="radio"] > div {
        background-color: #ac0000 !important;
        color: white !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }

    /* -------------------------------
       Area Grafik & Konten
    ------------------------------- */
    .block-container {
        background-color: #f8f9fa !important; /* putih keabu lembut */
        border-radius: 10px;
        padding: 20px;
    }
    
    /* Sensor Data Display */
    .sensor-data {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ac0000;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Title
# -------------------------------
st.markdown(
    "<h1 style='font-family: \"Archivo Black\", sans-serif; font-size: 30px; text-align:left;'>BLINKBand Simulation (Continuous Glucose Monitoring)</h1>",
    unsafe_allow_html=True
)

st.markdown(
    """
    <p style='text-align: left;
              font-family: "Roboto", sans-serif;
              font-size: 14px;
              color: #767676;
              margin-top: -15px;
              margin-bottom: 25px;'>
        made by <b>Dhimas Adjie Pradayan,</b> powered by <b>Python</b> via <b> Streamlit</b>
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <p style='text-align: left;
              font-family: "Roboto", sans-serif;
              font-size: 18px;
              color: #767676;
              margin-top: -15px;
              margin-bottom: 25px;'>
        Simulasi ini meniru interaksi antar data yang diinput dari semua sensor pada BlinkBand yang menghasilkan perkiraan kadar gula darah
    </p>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Data Source Selection
# -------------------------------
st.sidebar.header("Data Source Configuration")
data_source = st.sidebar.radio(
    "Select Data Source:",
    ["Simulated Data", "ESP32 Microcontroller"]
)

# -------------------------------
# Initialize Session States
# -------------------------------
if "running" not in st.session_state:
    st.session_state.running = False
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Time", "Glucose"])
if "t" not in st.session_state:
    st.session_state.t = 0
if "prev_glucose" not in st.session_state:
    st.session_state.prev_glucose = None
if "sensor_values" not in st.session_state:
    st.session_state.sensor_values = {
        "red_signal": 0.6,
        "ir_signal": 0.7,
        "temperature": 36.5,
        "motion": 0.3
    }
if "serial_connected" not in st.session_state:
    st.session_state.serial_connected = False
if "serial_port" not in st.session_state:
    st.session_state.serial_port = None

# -------------------------------
# Data Reception Functions
# -------------------------------
def connect_to_serial(port='COM3', baudrate=115200):
    """Connect to ESP32 via Serial"""
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Wait for connection
        return ser
    except Exception as e:
        st.error(f"Failed to connect to {port}: {e}")
        return None

def read_serial_data(ser):
    """Read and parse data from serial connection"""
    if ser and ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line.startswith("DATA:"):
                data_str = line[5:]  # Remove "DATA:" prefix
                values = data_str.split(',')
                if len(values) == 4:
                    return {
                        "red_signal": float(values[0]),
                        "ir_signal": float(values[1]),
                        "temperature": float(values[2]),
                        "motion": float(values[3])
                    }
        except Exception as e:
            st.warning(f"Error reading serial data: {e}")
    return None

def receive_http_data():
    """Receive data from HTTP endpoint (for WiFi connection)"""
    try:
        # This would be your ESP32's IP address
        response = requests.get('http://ESP32_IP_ADDRESS/data', timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None

# -------------------------------
# Sidebar Settings
# -------------------------------
st.sidebar.header("Sensor Input")

if data_source == "Simulated Data":
    # Use sliders for simulated data
    red_signal = st.sidebar.slider("Red Signal", 0.0, 1.0, 0.6, 0.01)
    ir_signal = st.sidebar.slider("IR Signal", 0.0, 1.0, 0.7, 0.01)
    temperature = st.sidebar.slider("Temperature (°C)", 30.0, 40.0, 36.5, 0.1)
    motion = st.sidebar.slider("Motion Activity", 0.0, 1.0, 0.3, 0.01)
    
    # Update session state
    st.session_state.sensor_values = {
        "red_signal": red_signal,
        "ir_signal": ir_signal,
        "temperature": temperature,
        "motion": motion
    }
    
else:  # ESP32 Microcontroller
    st.sidebar.info("Receiving data from ESP32...")
    
    # Serial port configuration
    serial_port = st.sidebar.text_input("Serial Port", "COM3")
    baud_rate = st.sidebar.selectbox("Baud Rate", [9600, 115200, 230400], index=1)
    
    col1, col2 = st.sidebar.columns(2)
    connect_btn = col1.button("Connect")
    disconnect_btn = col2.button("Disconnect")
    
    if connect_btn and not st.session_state.serial_connected:
        ser = connect_to_serial(serial_port, baud_rate)
        if ser:
            st.session_state.serial_port = ser
            st.session_state.serial_connected = True
            st.sidebar.success(f"Connected to {serial_port}")
    
    if disconnect_btn and st.session_state.serial_connected:
        if st.session_state.serial_port:
            st.session_state.serial_port.close()
        st.session_state.serial_connected = False
        st.session_state.serial_port = None
        st.sidebar.info("Disconnected")
    
    # Display current sensor values
    st.sidebar.markdown("### Current Sensor Readings")
    st.sidebar.markdown(f"""
    <div class='sensor-data'>
    <b>Red Signal:</b> {st.session_state.sensor_values['red_signal']:.2f}<br>
    <b>IR Signal:</b> {st.session_state.sensor_values['ir_signal']:.2f}<br>
    <b>Temperature:</b> {st.session_state.sensor_values['temperature']:.1f}°C<br>
    <b>Motion:</b> {st.session_state.sensor_values['motion']:.2f}
    </div>
    """, unsafe_allow_html=True)
    
    # Try to read from serial
    if st.session_state.serial_connected and st.session_state.serial_port:
        sensor_data = read_serial_data(st.session_state.serial_port)
        if sensor_data:
            st.session_state.sensor_values = sensor_data
    
    # Use session state values for calculations
    red_signal = st.session_state.sensor_values["red_signal"]
    ir_signal = st.session_state.sensor_values["ir_signal"]
    temperature = st.session_state.sensor_values["temperature"]
    motion = st.session_state.sensor_values["motion"]

# Common settings
duration = st.sidebar.number_input("Simulation Duration (seconds)", 10, 300, 30, step=5)

# -------------------------------
# Control Buttons
# -------------------------------
col1, col2 = st.columns(2)
start = col1.button("START Simulation", type="primary")
stop = col2.button("STOP Simulation")

if start:
    st.session_state.running = True
    st.session_state.data = pd.DataFrame(columns=["Time", "Glucose"])
    st.session_state.t = 0
    st.session_state.prev_glucose = None
elif stop:
    st.session_state.running = False

# -------------------------------
# Glucose Calculation Function
# -------------------------------
def calculate_glucose(red, ir, temp, motion, prev_glucose, t):
    # Sensitivitas Optik
    optical_effect = (2 - (red + ir)) * 90
    
    # Temperature effect
    temp_effect = (temp - 36.5) * 3
    
    # Motion effect
    motion_effect = -motion * 40
    
    # Circadian rhythm
    circadian_effect = 5 * np.sin(t / 15)
    
    # Random noise
    noise = np.random.normal(0, 2)
    
    glucose = optical_effect + temp_effect + motion_effect + circadian_effect + noise
    
    # Smoothing with previous value
    if prev_glucose is not None:
        glucose = 0.5 * prev_glucose + 0.5 * glucose
    
    # Clip to realistic range
    glucose = np.clip(glucose, 20, 200)
    
    return glucose

# -------------------------------
# Display Sensor Data
# -------------------------------
st.markdown("### Live Sensor Data")
data_cols = st.columns(4)
with data_cols[0]:
    st.metric("Red Signal", f"{red_signal:.2f}")
with data_cols[1]:
    st.metric("IR Signal", f"{ir_signal:.2f}")
with data_cols[2]:
    st.metric("Temperature", f"{temperature:.1f}°C")
with data_cols[3]:
    st.metric("Motion", f"{motion:.2f}")

# -------------------------------
# Placeholder Setup
# -------------------------------
status_placeholder = st.empty()
glucose_placeholder = st.empty()
chart_placeholder = st.empty()

# Initial chart
fig, ax = plt.subplots(figsize=(6, 3))
ax.set_xlabel("Time (hh:mm:ss)")
ax.set_ylabel("Glucose Level (mg/dL)")
ax.set_title("Real-Time Glucose Level Over Time")
ax.tick_params(axis='both', labelsize=8)
ax.title.set_fontsize(10)
ax.xaxis.label.set_size(9)
ax.yaxis.label.set_size(9)
ax.set_ylim(0, 200)
chart_placeholder.pyplot(fig)

# -------------------------------
# Main Simulation Loop
# -------------------------------
if st.session_state.running:
    status_placeholder.markdown("*Status:* Running...")
    prev_glucose = st.session_state.prev_glucose

    for i in range(duration):
        if not st.session_state.running:
            break

        # Update sensor values if using ESP32
        if data_source == "ESP32 Microcontroller" and st.session_state.serial_connected:
            sensor_data = read_serial_data(st.session_state.serial_port)
            if sensor_data:
                st.session_state.sensor_values = sensor_data
                red_signal = sensor_data["red_signal"]
                ir_signal = sensor_data["ir_signal"]
                temperature = sensor_data["temperature"]
                motion = sensor_data["motion"]

        st.session_state.t += 1
        timestamp = time.strftime("%H:%M:%S", time.localtime())

        glucose = calculate_glucose(
            red_signal, ir_signal, temperature, motion, prev_glucose, st.session_state.t
        )
        prev_glucose = glucose
        st.session_state.prev_glucose = glucose

        new_row = pd.DataFrame({"Time": [timestamp], "Glucose": [glucose]})
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)

        # Display glucose value
        glucose_placeholder.markdown(
            f"<div class='glucose-metric'>Kadar Gula Darah: <b>{glucose:.2f} mg/dL</b></h2>",
            unsafe_allow_html=True
        )

        # Update chart
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(st.session_state.data["Time"], st.session_state.data["Glucose"], color="red", linewidth=2)
        ax.set_xlabel("Time (hh:mm:ss)")
        ax.set_ylabel("Glucose Level (mg/dL)")
        ax.set_title("Real-Time Glucose Level Over Time")
        ax.tick_params(axis='both', labelsize=8)
        ax.title.set_fontsize(10)
        ax.xaxis.label.set_size(9)
        ax.yaxis.label.set_size(9)
        ax.set_ylim(0, 200)
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart_placeholder.pyplot(fig)

        time.sleep(1)

    st.session_state.running = False
    status_placeholder.markdown("*Status:* Simulation completed.")

else:
    if not st.session_state.data.empty:
        status_placeholder.markdown("*Status:* Stopped.")
        last_val = st.session_state.data["Glucose"].iloc[-1]
        glucose_placeholder.markdown(
            f"<div class='glucose-metric'>Kadar Gula Darah Terakhir: <b>{last_val:.2f} mg/dL</b></h2>",
            unsafe_allow_html=True
        )
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(st.session_state.data["Time"], st.session_state.data["Glucose"], color="red", linewidth=2)
        ax.set_xlabel("Time (hh:mm:ss)")
        ax.set_ylabel("Glucose Level (mg/dL)")
        ax.set_title("Glucose Level History")
        ax.tick_params(axis='both', labelsize=8)
        ax.title.set_fontsize(10)
        ax.xaxis.label.set_size(9)
        ax.yaxis.label.set_size(9)
        ax.set_ylim(0, 200)
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart_placeholder.pyplot(fig)
    else:
        st.info("Press 'Start Simulation' to begin.")

# -------------------------------
# Data Export
# -------------------------------
if not st.session_state.data.empty:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Data Export")
    
    # Convert to CSV
    csv = st.session_state.data.to_csv(index=False)
    st.sidebar.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"glucose_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
