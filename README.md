# syndigo_test

## To run the code 

scrapy crawl target -a url=https://www.target.com/p/-/A-79344798


## If you want the output in JSON file then put these lines before return clean_data

with open('output.json', 'w', encoding='utf-8') as json_file:
    json.dump(clean_data, json_file, ensure_ascii=False, indent=4)
return clean_data

## Scrapy file can be found in spiders/scrape.py