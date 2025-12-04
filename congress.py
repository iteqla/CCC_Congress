import requests
import csv
import re
from datetime import date

input_file = "entries.csv"
output_file = f"entries_updated_{date.today().isoformat()}.csv"
rating_date = date.today().isoformat()

#------- API URLs -------#
base_url_ecf = "https://rating.englishchess.org.uk/v2/new/api.php?v2"
base_url_fide = "https://api.chesstools.org/fide/"

#------- Extracts raw ECF code from a cell (HTML-wrapped or plain) -------#
def extract_ecf_code(cell):
    if not cell:
        return None
    match = re.search(r'\b([0-9]{6}[A-Z]|[A-Z]\d{5,6})\b', cell, re.IGNORECASE)
    return match.group(1).upper() if match else None

#------- Read input, process, write output -------#
with open(input_file, "r", newline="", encoding="utf-8") as infile, \
     open(output_file, "w", newline="", encoding="utf-8") as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    #------- Write header (copy exactly from input) -------#
    header = next(reader)
    writer.writerow(header)

    for row in reader:
        if not row:
            writer.writerow(row)        # Preserves empty lines
            continue

        raw_ecf_cell = row[0].strip()
        code = extract_ecf_code(raw_ecf_cell)

        if not code:
            #------- No valid ECF code → leave row untouched -------#
            writer.writerow(row)
            continue

        #------- Fetches fresh ECF data -------#
        info = requests.get(f"{base_url_ecf}/players/code/{code}").json()
        full_name = info.get("full_name", "")
        if "," in full_name:
            last, first = map(str.strip, full_name.split(",", 1))
        else:
            parts = full_name.split()
            first = parts[0] if parts else ""
            last = " ".join(parts[1:]) if len(parts) > 1 else ""

        club = info.get("club_name", "")
        fide_id = info.get("FIDE_no", "")
        ecf_membership = info.get("category", "")
        ecf_expiry = info.get("due_date", "")

        rating_ecf_resp = requests.get(
            f"{base_url_ecf}/ratings/S/{code}/{rating_date}"
        ).json()
        rating_ecf = rating_ecf_resp.get("original_rating", "")

        #------- FIDE rating -------#
        rating_fide = "N/A"
        if fide_id and str(fide_id).strip().isdigit():
            try:
                resp = requests.get(f"{base_url_fide}{fide_id}", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if "rating" in data and data["rating"] is not None:
                        rating_fide = str(data["rating"])
            except Exception:
                rating_fide = "Error"

        #------- Fresh HTML links -------#
        ecf_link = f'<a href="https://rating.englishchess.org.uk/players?player_no={code}" target="_blank">{code}</a>'
        fide_link = (f'<a href="https://ratings.fide.com/profile/{fide_id}" target="_blank">{fide_id}</a>'
                     if fide_id and str(fide_id).strip().isdigit() else
                     (fide_id if fide_id else ""))

        #------- Builds new row -------#
        new_row = [
            ecf_link,       # A: ECF Code (always fresh HTML)
            fide_link,      # B: FIDE ID (HTML only if valid)
            first,          # C
            last,           # D
            rating_ecf,     # E
            rating_fide,    # F
            ecf_membership, # G
            ecf_expiry,     # H
            club            # I
        ]

        #------- Appends everything from original row starting at index 9 (Section onwards) -------#
        new_row.extend(row[9:])
        writer.writerow(new_row)

print(f"Updated file saved as → {output_file}")
