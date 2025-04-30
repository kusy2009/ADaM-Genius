import os
import sys
import json
import argparse
import requests
import csv
from datetime import datetime

# Uncomment and use python-dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()

class ADaMMetadataRetriever:
    """Class for retrieving ADaM variable metadata from the CDISC Library API."""

    # Base URL for the CDISC Library API
    BASE_URL = "https://library.cdisc.org/api"

    def __init__(self, api_key=None):
        """Initialize the retriever with an API key from environment or parameter."""
        # Prioritize parameter, then environment variable
        self.api_key = api_key or os.getenv('CDISC_API_KEY')
        
        if not self.api_key:
            raise ValueError("CDISC API key is required. Set CDISC_API_KEY in .env file or pass as parameter.")
        
        self.headers = {
            "api-key": self.api_key,
            "Accept": "application/json"
        }

    def _make_request(self, url):
        """Helper function to make API requests."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ERROR: API request failed for {url}. Error: {e}")
            # Attempt to parse error details from response if available
            try:
                error_details = response.json()
                print(f"API Error Details: {json.dumps(error_details, indent=2)}")
            except (AttributeError, json.JSONDecodeError):
                pass # No JSON body or response object doesn't exist
            return None
        except json.JSONDecodeError:
            print(f"ERROR: Failed to decode JSON response from {url}")
            print(f"Response text: {response.text[:500]}...") # Print first 500 chars
            return None

    # Removed get_latest_adamig_version function as per reference script analysis
    # def get_latest_adamig_version(self): ...

    def get_latest_ct_version_for_standard(self, standard):
        """Retrieve the latest Controlled Terminology version for a given standard (e.g., adamct, sdtmct)."""
        print(f"Fetching latest {standard} version...")
        url = f"{self.BASE_URL}/mdr/products/Terminology"
        data = self._make_request(url)

        if not data or "_links" not in data or "packages" not in data["_links"]:
            print(f"ERROR: Could not find Terminology packages in API response.")
            return None

        ct_links = data["_links"]["packages"]
        versions = []
        package_prefix = f"/{standard}-" # e.g., /adamct- or /sdtmct-
        for link in ct_links:
            href = link.get("href", "")
            # Look for packages like /mdr/ct/packages/adamct-YYYY-MM-DD or /mdr/ct/packages/sdtmct-YYYY-MM-DD
            if package_prefix in href:
                try:
                    version_date = href.split(package_prefix)[-1]
                    # Validate date format YYYY-MM-DD
                    datetime.strptime(version_date, '%Y-%m-%d') # Corrected quotes
                    versions.append(version_date)
                except (IndexError, ValueError):
                    continue # Skip if format is wrong

        if not versions:
            print(f"ERROR: No {standard} versions found.")
            return None

        # Sort dates chronologically
        latest_version = sorted(versions, reverse=True)[0]
        print(f"Latest {standard} version found: {latest_version}")
        return latest_version

    def _find_variable_dataset(self, adam_variable, adamig_version):
        """Determine the dataset structure name (e.g., ADSL, OCCDS) for a given variable."""
        # Ensure adamig_version uses hyphen format (e.g., "1-3")
        adamig_version_hyphen = adamig_version.replace(".", "-")
        print(f"Fetching ADaMIG structure for version {adamig_version_hyphen} to find dataset for {adam_variable}...")
        url = f"{self.BASE_URL}/mdr/adam/adamig-{adamig_version_hyphen}"
        data = self._make_request(url)

        if not data or "dataStructures" not in data:
            print(f"ERROR: Could not fetch or parse ADaMIG structure for version {adamig_version_hyphen}.")
            return None

        # Simplified logic: Iterate through structures and variables directly
        for ds in data.get("dataStructures", []):
            ds_name = ds.get("name")
            if not ds_name:
                continue # Skip structures without a name

            # Check variables directly within the data structure (less common but possible)
            for var in ds.get("analysisVariables", []): # Check top-level vars in DS first
                 if var.get("name", "").upper() == adam_variable.upper():
                     print(f"Variable {adam_variable} found directly in dataset structure: {ds_name}")
                     return ds_name

            # Check variables within analysisVariableSets (more common)
            for var_set in ds.get("analysisVariableSets", []):
                for var in var_set.get("analysisVariables", []):
                    if var.get("name", "").upper() == adam_variable.upper():
                        print(f"Variable {adam_variable} found in dataset structure: {ds_name}")
                        return ds_name # Return the name of the structure containing the variable

        print(f"ERROR: Variable 	{adam_variable}	 not found in any dataset structure for ADaMIG {adamig_version_hyphen}.")
        return None

    def get_variable_details(self, adam_variable, adamig_version):
        """Fetch details for a specific ADaM variable."""
        # ADaMIG version is now required
        if not adamig_version:
             raise ValueError("ADaMIG version is required.")

        # Ensure hyphen format
        adamig_version_hyphen = adamig_version.replace('.', '-')

        dataset = self._find_variable_dataset(adam_variable, adamig_version_hyphen)
        if not dataset:
            # Error message already printed in _find_variable_dataset
            return None

        print(f"Fetching details for {dataset}.{adam_variable} (ADaMIG {adamig_version_hyphen})...")
        url = f"{self.BASE_URL}/mdr/adam/adamig-{adamig_version_hyphen}/datastructures/{dataset}/variables/{adam_variable}"
        data = self._make_request(url)

        if not data:
            print(f"ERROR: Could not fetch details for variable {adam_variable} in dataset {dataset}.")
            return None

        # Extract key details (similar to SAS macro output)
        details = {
            "Variable": data.get("name"),
            "Label": data.get("label"),
            "DataType": data.get("simpleDatatype"),
            "Core": data.get("core"),
            "CDISCNotes": data.get("description"), # Or use 'definition' if more appropriate
            "Dataset": dataset, # Add the dataset context
            "ADaMIGVersion": adamig_version_hyphen, # Store the version used
            "CodelistLinks": [],
            "Codelists": [] # To store fetched codelist details later
        }

        # Extract codelist links and determine standard
        codelist_info_list = [] # Store tuples of (codelist_id, standard, href)
        if "_links" in data and "codelist" in data["_links"]:
            for link in data["_links"]["codelist"]:
                href = link.get("href")
                if href:
                    details["CodelistLinks"].append(href)
                    try:
                        # Example href: /mdr/root/ct/sdtmct/codelists/C66781
                        parts = href.split("/")
                        codelist_id = parts[-1]
                        standard = parts[-3] # Should be sdtmct or adamct
                        if codelist_id.startswith("C") and codelist_id[1:].isdigit() and standard in ["sdtmct", "adamct"]:
                            codelist_info_list.append((codelist_id, standard, href))
                        else:
                            print(f"Warning: Could not parse standard/ID from codelist href: {href}")
                    except IndexError:
                        print(f"Warning: Could not parse codelist href: {href}")
                        continue

        if codelist_info_list:
            unique_codelists = {info[0]: info for info in codelist_info_list}.values() # Deduplicate by ID
            codelist_summary = ", ".join([f"{info[0]} ({info[1]})" for info in unique_codelists])
            print(f"Found codelist references: {codelist_summary}")

            # Fetch terms for these codelists
            fetched_versions = {} # Cache fetched versions per standard
            for cl_id, standard, href in unique_codelists:
                if standard not in fetched_versions:
                    ct_version = self.get_latest_ct_version_for_standard(standard)
                    if not ct_version:
                        print(f"Warning: Could not fetch latest {standard} version, skipping codelist {cl_id}.")
                        fetched_versions[standard] = None # Mark as failed
                        continue
                    fetched_versions[standard] = ct_version
                
                ct_version = fetched_versions[standard]
                if ct_version:
                    # Pass standard and version to get_codelist_terms
                    codelist_data = self.get_codelist_terms(cl_id, standard, ct_version)
                    if codelist_data:
                        details["Codelists"].append(codelist_data)
                # else: Warning already printed
        else:
            print("No codelist references found for this variable.")

        return details

    def get_codelist_terms(self, codelist_code, standard, ct_version):
        """Fetch terms for a specific codelist code from the specified CT package (standard and version)."""
        print(f"Fetching terms for Codelist Code {codelist_code} ({standard} version {ct_version})...")
        # Construct URL using the provided standard
        url = f"{self.BASE_URL}/mdr/ct/packages/{standard}-{ct_version}"
        data = self._make_request(url)

        if not data or "codelists" not in data:
            print(f"ERROR: Could not fetch or parse {standard} package version {ct_version}.")
            return None

        target_codelist = None
        for codelist in data.get("codelists", []):
            # Match using conceptId (C-code)
            if codelist.get("conceptId", "").upper() == codelist_code.upper():
                target_codelist = codelist
                break

        if not target_codelist:
            # Also check submissionValue as a fallback, though conceptId is preferred
            for codelist in data.get("codelists", []):
                 if codelist.get("submissionValue", "").upper() == codelist_code.upper():
                     target_codelist = codelist
                     print(f"Note: Matched codelist {codelist_code} using submissionValue.")
                     break

        if not target_codelist:
            print(f"WARNING: Codelist Code 	{codelist_code}	 not found in {standard} version {ct_version}.")
            return None

        # Process the target codelist (similar to cdisc_codelist.py)
        cl_info = {
            "ID": target_codelist.get("submissionValue", ""),
            "CodelistCode": target_codelist.get("conceptId", ""),
            "Name": target_codelist.get("name", ""),
            "ExtensibleYN": "Yes" if target_codelist.get("extensible", False) else "No",
            "Standard": standard, # Add standard info
            "Version": ct_version, # Add version info
            "Terms": []
        }

        for term in target_codelist.get("terms", []):
            cl_info["Terms"].append({
                "TermCode": term.get("conceptId", ""),
                "TERM": term.get("submissionValue", ""),
                "TermDecodedValue": term.get("preferredTerm", "")
            })

        # Sort terms by submission value
        cl_info["Terms"].sort(key=lambda x: x.get("TERM", ""))
        # Extract values before f-string to avoid quote issues
        num_terms = len(cl_info["Terms"])
        cl_id = cl_info["ID"]
        cl_code = cl_info["CodelistCode"]
        print(f"Successfully fetched {num_terms} terms for {cl_id} ({cl_code} from {standard} {ct_version}).")
        return cl_info

def display_variable_details(details):
    """Display variable details and associated codelists in a formatted way."""
    if not details:
        print("No details to display.")
        return

    print("\n" + "="*70)
    print(f" ADaM Variable Details: {details.get('Dataset', 'N/A')}.{details.get('Variable', 'N/A')}")
    print(f" ADaMIG Version: {details.get('ADaMIGVersion', 'N/A')}")
    print("="*70)
    print(f"  Label:        {details.get('Label', 'N/A')}")
    print(f"  Data Type:    {details.get('DataType', 'N/A')}")
    print(f"  Core Status:  {details.get('Core', 'N/A')}")
    print(f"  CDISC Notes:  {details.get('CDISCNotes', 'N/A')}")
    print(f"  Codelist HREFs: {', '.join(details.get('CodelistLinks', ['N/A']))}")

    if details.get("Codelists"):
        print("\n" + "-"*70)
        print(" Associated Codelist(s)")
        print("-"*70)
        for cl in details["Codelists"]:
            print(f"\n  Codelist:     {cl.get('Name', 'N/A')} ({cl.get('ID', 'N/A')}) [{cl.get('CodelistCode', 'N/A')}]")
            print(f"  Extensible:   {cl.get('ExtensibleYN', 'N/A')}")
            print("  Terms:")
            if cl.get("Terms"):
                print("    {:<20} {:<40}".format("TERM", "Decoded Value"))
                print("    " + "-" * 62)
                for term in cl["Terms"]:
                    print("    {:<20} {:<40}".format(term.get("TERM", ""), term.get("TermDecodedValue", "")))
            else:
                print("    No terms found.")
    else:
        print("\nNo associated codelist terms were fetched or found.")
    print("\n" + "="*70)

def write_to_csv(details, output_file):
    """Write variable details and terms to a CSV file."""
    if not details:
        print("No details to write to CSV.")
        return

    rows = []
    # Basic variable info
    var_info = {
        "Parameter": "Variable", "Value": details.get('Variable', 'N/A'),
        "Dataset": details.get('Dataset', 'N/A'), "ADaMIGVersion": details.get('ADaMIGVersion', 'N/A'),
        "CodelistID": "", "CodelistCode": "", "CodelistName": "", "ExtensibleYN": "",
        "TermCode": "", "TERM": "", "TermDecodedValue": ""
    }
    rows.append({**var_info, "Parameter": "Label", "Value": details.get('Label', 'N/A')})
    rows.append({**var_info, "Parameter": "DataType", "Value": details.get('DataType', 'N/A')})
    rows.append({**var_info, "Parameter": "Core", "Value": details.get('Core', 'N/A')})
    rows.append({**var_info, "Parameter": "CDISCNotes", "Value": details.get('CDISCNotes', 'N/A')})
    rows.append({**var_info, "Parameter": "CodelistLinks", "Value": ', '.join(details.get('CodelistLinks', []))})

    # Codelist info and terms
    if details.get("Codelists"):
        for cl in details["Codelists"]:
            cl_base_info = {
                "Parameter": "CodelistTerm", "Value": "",
                "Dataset": details.get('Dataset', 'N/A'), "ADaMIGVersion": details.get('ADaMIGVersion', 'N/A'),
                "CodelistID": cl.get('ID', 'N/A'), "CodelistCode": cl.get('CodelistCode', 'N/A'),
                "CodelistName": cl.get('Name', 'N/A'), "ExtensibleYN": cl.get('ExtensibleYN', 'N/A')
            }
            if cl.get("Terms"):
                for term in cl["Terms"]:
                    rows.append({
                        **cl_base_info,
                        "TermCode": term.get("TermCode", ""),
                        "TERM": term.get("TERM", ""),
                        "TermDecodedValue": term.get("TermDecodedValue", "")
                    })
            else:
                 # Add a row indicating no terms for this codelist
                 rows.append({**cl_base_info, "TERM": "(No terms found)"})

    if not rows:
        print("No data generated for CSV.")
        return

    fieldnames = ["Dataset", "ADaMIGVersion", "Parameter", "Value", "CodelistID", "CodelistCode", "CodelistName", "ExtensibleYN", "TermCode", "TERM", "TermDecodedValue"]

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nResults saved to {output_file}")
    except IOError as e:
        print(f"ERROR: Could not write to CSV file {output_file}. Error: {e}")

def main():
    """Main function to run from command line."""
    parser = argparse.ArgumentParser(description='Retrieve ADaM variable metadata from CDISC Library API')
    parser.add_argument('adam_variable', help='The ADaM variable name (e.g., TRT01P, PARAMCD)')
    # Make adamig_version required or default to '1-3'
    parser.add_argument('--adamig_version', default='1-3', help='Specific ADaMIG version (e.g., 1-3). Defaults to 1-3.')
    parser.add_argument('--api_key', help='CDISC Library API key (optional, use .env file instead)')
    parser.add_argument('--output', help='Output CSV file path')

    args = parser.parse_args()

    try:
        print("ADaM Metadata Retrieval Tool")
        print("============================")

        retriever = ADaMMetadataRetriever(api_key=args.api_key)
        # Pass the required adamig_version
        result = retriever.get_variable_details(
            adam_variable=args.adam_variable,
            adamig_version=args.adamig_version
        )

        if result:
            display_variable_details(result)
            if args.output:
                write_to_csv(result, args.output)
        else:
            print(f"\nCould not retrieve details for variable '{args.adam_variable}'.")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        sys.exit(1)

if __name__ == "__main__":
    main()
