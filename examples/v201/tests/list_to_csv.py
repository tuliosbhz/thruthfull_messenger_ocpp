import json
import csv

# Read JSON data from file
with open('rtt_ocpp_messages.txt', 'r') as file:
    data = json.load(file)

# Prepare CSV data
csv_data = []
csv_data.append(["Data hora", "RTT"])
for rtt_value in data["RTT"]:
    csv_data.append([data["Data hora"], rtt_value])

# Write CSV data to file
with open('rtt_ocpp_messages.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(csv_data)

print("CSV file created successfully.")
