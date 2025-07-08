import serial as serial
import requests
import json
import re
import time
from datetime import datetime

# Serial port configuration (adjust as needed)
SERIAL_PORT = '/dev/tty.usbmodem0010502681671'
BAUD_RATE = 115200

# Server configuration
SERVER_URL = 'http://localhost:8000/api/readings'

# Buffer for incomplete data packets
data_buffer = ""


def connect_serial():
    """Establish serial connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"Connected to {SERIAL_PORT} (attempt {attempt + 1})")
            return ser
        except serial.SerialException as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise


def clean_data(raw_line):
    """Remove ANSI escape sequences and control characters, but be more lenient"""
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[mK]?')
    cleaned = ansi_escape.sub('', raw_line)

    # Only remove the most problematic control characters, keep printable ones
    # Remove null bytes, carriage returns, and form feeds, but keep tabs and spaces
    control_chars = re.compile(r'[\x00\x0c\x0e-\x1f\x7f-\x9f]')
    cleaned = control_chars.sub('', cleaned)

    return cleaned.strip()


def is_uart_noise(line):
    """Check if the line is UART noise or terminal output to ignore"""
    if not line:
        return True

    # Common UART/terminal patterns to ignore
    noise_patterns = [
        r'uart:~?\$',          # UART prompt
        r'^\s*\$',             # Shell prompt
        r'^\s*#',              # Root prompt
        r'command not found',   # Error messages
        r'error:',
        r'failed:',
        r'warning:',
        r'debug:',
        r'info:',
        r'^\s*\[.*\]',         # Log entries with brackets
        r'^\s*\w+>',           # Command prompts
        r'^\s*>',              # Simple prompt
    ]

    line_lower = line.lower().strip()
    for pattern in noise_patterns:
        if re.search(pattern, line_lower):
            return True

    return False


def extract_data_packets(buffer_content):
    """Extract complete data packets from buffer using <DATA></DATA> delimiters"""
    packets = []
    remaining_buffer = buffer_content

    # Find all complete packets
    pattern = r'<DATA>(.*?)</DATA>'
    matches = re.finditer(pattern, buffer_content, re.DOTALL)

    last_end = 0
    for match in matches:
        data_content = match.group(1).strip()
        if data_content:  # Only add non-empty packets
            packets.append(data_content)
        last_end = match.end()

    # Keep any remaining incomplete data in buffer
    remaining_buffer = buffer_content[last_end:]

    # If there's a partial <DATA> tag at the end, keep it
    if '<DATA>' in remaining_buffer and '</DATA>' not in remaining_buffer:
        # Keep the partial packet for next iteration
        pass
    else:
        # Clear buffer if no partial packet
        remaining_buffer = ""

    return packets, remaining_buffer


def extract_numbers_from_text(text):
    """Extract numeric values from potentially corrupted text"""
    # Find all sequences that look like numbers (including decimals)
    number_pattern = re.compile(r'-?\d+\.?\d*')
    numbers = number_pattern.findall(text)
    return [float(num) for num in numbers if num and ('.' in num or num.isdigit())]


def is_valid_sensor_data(line):
    """Check if the line contains valid sensor data - made more lenient"""
    if not line:
        return False

    # Try to extract numbers from the line
    numbers = extract_numbers_from_text(line)

    # We need at least 6 numbers for one complete sensor reading
    if len(numbers) < 6:
        return False

    # Check if we have multiples of 6 numbers (for multiple readings)
    if len(numbers) % 6 != 0:
        # If not exact multiple of 6, see if we can work with what we have
        # Maybe truncate to largest complete set
        complete_sets = len(numbers) // 6
        if complete_sets == 0:
            return False
        # We'll work with the complete sets we have
        numbers = numbers[:complete_sets * 6]

    # Basic sanity checks for sensor values - made more lenient
    for i, value in enumerate(numbers):
        sensor_type = i % 6  # 0=CO2, 1=temp, 2=humidity, 3=VOCs, 4=PM2.5, 5=PM10

        # Very broad range checks - mainly to catch obviously wrong values
        if value < -100 or value > 100000:  # Very generous bounds
            return False

        # More lenient specific checks
        if sensor_type == 0 and value < 50:  # CO2 - allow very low values
            return False
        # Temperature - broader range
        if sensor_type == 1 and (value < -50 or value > 100):
            return False
        # Humidity - slight tolerance
        if sensor_type == 2 and (value < 0 or value > 105):
            return False

    return True


def parse_data_packet(data_content):
    """
    Parse a single data packet extracted from <DATA></DATA> delimiters
    """
    try:
        print(f"Parsing packet: {repr(data_content)}")

        # Try original semicolon-delimited format first
        if ';' in data_content and ',' in data_content:
            entries = [entry.strip()
                       for entry in data_content.split(';') if entry.strip()]

            parsed_entries = []
            for entry in entries:
                parts = entry.split(',')
                if len(parts) >= 6:  # At least 6 values
                    try:
                        parsed_entry = {
                            "co2": float(parts[0].strip()),
                            "temperature": float(parts[1].strip()),
                            "humidity": float(parts[2].strip()),
                            "vocs": float(parts[3].strip()),
                            "pm25": float(parts[4].strip()),
                            "pm10": float(parts[5].strip()),
                            "timestamp": datetime.now().isoformat(timespec='seconds')
                        }
                        parsed_entries.append(parsed_entry)
                    except (ValueError, IndexError) as e:
                        print(f"Failed to parse entry '{entry}': {e}")
                        continue

            if parsed_entries:
                return parsed_entries

        # If semicolon format failed, try to extract numbers directly
        print("Semicolon format failed, trying number extraction...")
        if is_valid_sensor_data(data_content):
            numbers = extract_numbers_from_text(data_content)
            print(f"Extracted numbers: {numbers}")

            # Group numbers into sets of 6
            parsed_entries = []
            # Step by 6, ensure we have at least 6 numbers
            for i in range(0, len(numbers) - 5, 6):
                try:
                    parsed_entry = {
                        "co2": numbers[i],
                        "temperature": numbers[i + 1],
                        "humidity": numbers[i + 2],
                        "vocs": numbers[i + 3],
                        "pm25": numbers[i + 4],
                        "pm10": numbers[i + 5],
                        "timestamp": datetime.now().isoformat(timespec='seconds')
                    }
                    parsed_entries.append(parsed_entry)
                except (IndexError, ValueError) as e:
                    print(
                        f"Failed to parse number set starting at index {i}: {e}")
                    continue

            if parsed_entries:
                print(
                    f"Successfully parsed {len(parsed_entries)} entries using number extraction")
                return parsed_entries

        print("No valid data could be extracted from packet")
        return None

    except Exception as e:
        print(f"Failed to parse packet: {e}")
        return None


def parse_data(raw_line):
    """
    Legacy function - now just a wrapper for backward compatibility
    """
    return parse_data_packet(raw_line)


# Main execution loop
ser = None
try:
    ser = connect_serial()
    print(f"Listening on {SERIAL_PORT}...")
    print("Looking for data packets in format: <DATA>sensor_data</DATA>")

    while True:
        try:
            raw_bytes = ser.readline()
            if raw_bytes:
                # Debug: show raw bytes
                print("Raw bytes:", raw_bytes)

                # Try different decoding approaches
                try:
                    # First try ASCII since sensor data should be simple ASCII
                    raw = raw_bytes.decode('ascii').strip()
                    print("Decoded as ASCII:", repr(raw))
                except UnicodeDecodeError:
                    try:
                        # Fall back to latin-1 (never fails, 1:1 byte mapping)
                        raw = raw_bytes.decode('latin-1').strip()
                        print("Decoded as latin-1:", repr(raw))
                    except:
                        # Last resort: UTF-8 with replacement
                        raw = raw_bytes.decode(
                            'utf-8', errors='replace').strip()
                        print("Decoded as UTF-8 with replacement:", repr(raw))

                if raw:
                    # Clean the data
                    cleaned = clean_data(raw)
                    print("Cleaned:", repr(cleaned))

                    # Add to buffer first - don't filter UART noise yet
                    # since
                    # there might be valid data packets mixed with noise
                    data_buffer += cleaned + '\n'
                    print(f"Buffer now contains: {repr(data_buffer)}")

                    # Extract complete packets from buffer
                    packets, data_buffer = extract_data_packets(data_buffer)

                    if packets:
                        print(f"Found {len(packets)} complete data packets")

                        for packet_idx, packet_data in enumerate(packets):
                            print(
                                f"\n--- Processing packet {packet_idx + 1} ---")
                            parsed_data_list = parse_data_packet(packet_data)

                            if parsed_data_list:
                                print(
                                    f"Parsed {len(parsed_data_list)} data entries from packet:")
                                for i, data in enumerate(parsed_data_list):
                                    print(f"  Entry {i+1}: {data}")
                                    try:
                                        response = requests.post(
                                            SERVER_URL,
                                            headers={
                                                "Content-Type": "application/json"},
                                            data=json.dumps(data),
                                            timeout=5
                                        )
                                        print(
                                            f"  Sent entry {i+1} to server: {response.status_code} {response.text}")
                                    except requests.RequestException as e:
                                        print(
                                            f"  Failed to send entry {i+1} to server: {e}")
                            else:
                                print(
                                    f"Could not parse packet {packet_idx + 1}: {repr(packet_data)}")

                    # Show buffer status and check if remaining buffer is just noise
                    if data_buffer:
                        # If buffer contains only UART noise (no DATA tags), clear it
                        if '<DATA>' not in data_buffer and is_uart_noise(data_buffer.strip()):
                            print(
                                f"Clearing UART noise from buffer: {repr(data_buffer.strip())}")
                            data_buffer = ""
                        else:
                            print(
                                f"Partial data in buffer: {repr(data_buffer)}")

        except serial.SerialException as e:
            print(f"Serial error: {e}")
            print("Attempting to reconnect...")
            try:
                if ser:
                    ser.close()
                time.sleep(2)
                ser = connect_serial()
                print("Reconnected successfully")
            except Exception as reconnect_error:
                print(f"Reconnection failed: {reconnect_error}")
                break

        except UnicodeDecodeError as e:
            print(f"Unicode decode error: {e}, skipping line")
            continue

except KeyboardInterrupt:
    print("Stopped by user.")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    if ser and ser.is_open:
        ser.close()
        print("Serial connection closed.")
