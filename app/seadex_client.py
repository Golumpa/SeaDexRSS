import json

import aiohttp


class RestApiClient:
    def __init__(self):
        self.base_url = "https://releases.moe/api"
        self.collection = "entries"

    async def get_entry(self, anilist_id: int):
        url = f"{self.base_url}/collections/{self.collection}/records"
        params = {"filter": f"alID={anilist_id}", "expand": "trs"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("items") and len(data["items"]) > 0:
                            return data["items"][0]
                        else:
                            print(f"No entry found for Anilist ID {anilist_id}")
                            return None
                    else:
                        response_text = await response.text()
                        print(
                            f"Error fetching entry: Status code: {response.status}, Response: {response_text}"
                        )
                        return None
            except aiohttp.ClientError as e:
                print(f"Network error while fetching entry: {str(e)}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON response: {str(e)}")
                return None
