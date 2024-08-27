import os
import aiofiles
import csv

class AsyncCsvWriter(object):
    def __init__(self):
        pass

    async def write_header_if_needed(self, file_name, header):
        if not os.path.exists(file_name):
            async with aiofiles.open(file_name, mode='w', newline='') as f:
                writer = csv.writer(f)
                await writer.writerow(header)

    async def write_row(self, data, file_name):
        async with aiofiles.open(file_name, mode='a', newline='') as f:
            writer = csv.writer(f)
            await writer.writerow(data)

    async def write_rows(self, data, file_name):
        # async with aiofiles.open(file_name, mode='a', newline='') as f:
        with open(file_name, mode='a', newline='') as f:
            writer = csv.writer(f)
            for row in data:
                await writer.writerow(row)

    async def remove_file(self, file_name):
        if os.path.exists(file_name):
            os.remove(file_name)



