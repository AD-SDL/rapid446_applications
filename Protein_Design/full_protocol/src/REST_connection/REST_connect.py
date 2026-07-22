

import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import traceback
import time

# TODO: is there a way to load in env variables without dotenv package? - Probably

load_dotenv(override=True)  # loads variables from .env into environment


class RESTHandlerPD:
    """
    Object for handling all communication with the Protein Design
    REST server.
    """

    def __init__(self):
        """Initializes the class"""
        # Extract the API key and base URL from the .env file
        self.api_key = os.getenv("PROTEIN_DESIGN_API_KEY")
        self.base_url = os.getenv("PROTEIN_DESIGN_BASE_URL")

    def authorize(self, session) -> requests.Session:
        """Opens a session and competes authorization"""

        # Initial authorization: Get token and session ID
        auth_url = f"{self.base_url}/auth/token"
        auth_payload = {"apiKey": self.api_key}
        token_response = session.post(auth_url, json=auth_payload).json()
        session_id = token_response['session_id']

        # return the session id
        return session_id


    def upload_excel_file(self, excel_path: str) -> int:
        """Uploads an Excel file to the upload blob endpoint.

        Args:
            excel_path (str): path to the excel file you wish to upload.

        Returns:
            oracle_id (int): oracle ID that was used to store the excel file in the database

        """

        upload_blob_url = f"{self.base_url}/excel/upload/blob"

        with requests.Session() as session:
            # Authenticate and set Bearer token.
            session_id = self.authorize(session)
            session.headers.update({"Authorization": f"Bearer {session_id}"})

            # Upload the data file.
            with open(excel_path, "rb") as f:
                response = session.post(upload_blob_url, files = {"file":f})
                oracle_id = response.json()['oracle_id']
                return oracle_id


    def collect_combinations(self, oracle_id: int, timeout: int = 600) -> dict:
        """
        Collects the combinations data dictionary from the combinations endpoit
        using the oracle ID from the most recent/relevant data file upload.

        Args:
            oracle_id (int): Oracle ID associated with the most recent Excel file upload
            timeout (int): Timeout value in seconds

        Returns:
            data =  238{
                'combinations': 2D array of combinations,
                'use_combinations': a boolean,
                'non_combinatiorial_sources': a 2D array
            }
        """
        collect_combinations_url =  f"{self.base_url}/combinations"
        start_time = time.time()

        with requests.Session() as session:
            # Authenticate and set the Bearer token
            session_id = self.authorize(session)
            session.headers.update({"Authorization": f"Bearer {session_id}"})

            while True:
                try:
                    response = session.get(collect_combinations_url, params={"oracle_id": oracle_id})
                    # response.raise_for_status()  # maybe raise exception for bad HTTP responses
                    data = response.json().get('data')
                    if data is not None:
                        return data  # return if sucessful
                except Exception as e:
                    print(f"Exception: {e}")
                    traceback.print_exc()

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Timed out after {timeout} seconds waiting for combinations data.")

                time.sleep(5)  # wait before retrying


if __name__ == "__main__":
    rest_handler = RESTHandlerPD()

    test_excel_path = "/home/rpl/workspace/rapid446_applications/Protein_Design/REST_connection/TEST_FullPlate_LDRD_run03_Hidex.xlsx"

    # # test uploading an excel file
    # oracle_id = rest_handler.upload_excel_file(test_excel_path)
    # print(oracle_id)

    # # test collecting the 2D arrays and data
    # data = rest_handler.collect_combinations(oracle_id=1008)
    # print(data)






