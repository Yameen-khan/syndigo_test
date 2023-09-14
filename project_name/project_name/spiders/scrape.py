from html import unescape
import re
import codecs
import ast
import scrapy


class TargetSpider(scrapy.Spider):
    name = 'target'

    def start_requests(self):
        product_url = getattr(self, 'url', None)
        if product_url:
            yield scrapy.Request(url=product_url, callback=self.parse)
        else:
            self.log("Please provide a valid 'url' argument")

    def parse(self, response):
        # Extract visitor_id
        get_data = response.xpath('//script[contains(text(), "__CONFIG__")]/text()').get()
        if get_data:
            data = self.extract_data_from_visitor_id(get_data)

            clean_data = self.clean_data(data)
            clean_data['url'] = response.url
            api_keys = re.findall(r'\\"apiKey\\":\\"([^\\"]+)\\"', get_data)
            api_key = api_keys[-1]
            TCIN = clean_data.get('TCIN')
            url_review = f"https://r2d2.target.com/ggc/v2/summary?key={api_key}&hasOnlyPhotos=false&includes=reviews%2CreviewsWithPhotos%2Centities%2Cmetadata%2Cstatistics&page=0&entity=&reviewedId={TCIN}&reviewType=PRODUCT&size=8&sortBy=most_recent&verifiedOnly=false"

            yield scrapy.Request(
                url_review,
                callback=self.review_parse,
                cb_kwargs={'clean_data': clean_data}
            )

    def review_parse(self, response, clean_data):
        data = response.json()
        results = data.get('reviews', {}).get('results', [])
        questions_list = []  # Initialize an empty list to store all questions

        for question in results:
            question_dict = {
                "question_id": question.get("id"),
                "submission_date": question.get("submitted_at"),
                "question_summary": question.get("text"),
                "user_nickname": question.get("nickname"),
                "answers": []
            }

            answers_list = question.get("ClientResponses", [])

            for answer in answers_list:
                answer_dict = {
                    "answer_summary": answer.get("text"),
                    "submission_date": answer.get("submitted_at"),
                    "user_nickname": answer.get("channel")
                }
                question_dict["answers"].append(answer_dict)

            questions_list.append(question_dict)

        clean_data["questions"] = questions_list
        return clean_data

    @staticmethod
    def extract_data_from_visitor_id(get_data):
        data = {}

        match_bullet = re.search(r'\\"soft_bullets\\":{\\"bullets\\":\[(.*?)\]', get_data)
        if match_bullet:
            bullets_section = match_bullet.group(1)
            cleaned_bullets = [bullet.strip() for bullet in re.findall(r'\\"(.*?)\\"', bullets_section)]
            data['bullet'] = cleaned_bullets

        match_description = re.search(r'\\"downstream_description\\":\\"(.*?)\\"', get_data)
        if match_description:
            data['description'] = match_description.group(1)

        match_features = re.search(r'\\"product_description\\":\{[^\}]+\}', get_data)
        if match_features:
            data['features'] = match_features.group()

        match_tcin = re.search(r'\\"tcin\\":\\"([^\\"]+)\\"', get_data)
        if match_tcin:
            data['TCIN'] = match_tcin.group()

        match_upc = re.search(r'\\"primary_barcode\\":\\"([^\\"]+)\\"', get_data)
        if match_upc:
            data['UPC'] = match_upc.group()

        match_price = re.search(r'\\"price\\":\{[^\}]+\}', get_data)
        if match_price:
            data['Price'] = match_price.group()

        return data

    @staticmethod
    def clean_data(raw_data):
        cleaned_data = {}

        bullets = raw_data.get('bullet', [])
        cleaned_data['bullets'] = [unescape(b.strip()) for b in bullets]

        unicode = unescape(raw_data.get('description', ''))
        unicode_unescaped = codecs.decode(unicode, 'unicode_escape')
        cleaned_str = re.sub(r'<br\s*/?>', ' ', unicode_unescaped)
        cleaned_data['description'] = cleaned_str

        cleaned_data['specs'] = ""

        cleaned_data['ingredients'] = ""

        price_data = raw_data.get('Price', '')
        match = re.search(r'\\"formatted_current_price\\":\\"(.*?)\\"', price_data)
        cleaned_data['price_amount'] = match.group(1)
        cleaned_data['currency'] = 'USD'  # Assuming currency is always in USD

        features = raw_data.get('features')
        unicode_unescaped = codecs.decode(features, 'unicode_escape')
        start_index = unicode_unescaped.find('"bullet_descriptions":[')
        end_index = unicode_unescaped.find(']', start_index) + 1
        bullet_descriptions_str = unicode_unescaped[start_index:end_index]
        bullet_descriptions_str = bullet_descriptions_str.replace('<B>', '').replace('</B>', '')
        modified_json = bullet_descriptions_str.replace('"bullet_descriptions"', '"features"')
        dictionary = ast.literal_eval("{" + modified_json + "}")
        cleaned_data['features'] = dictionary['features']

        data_str = raw_data.get('UPC')
        clean_data_str = data_str.replace('\\', '').replace('"', '')
        key, value = clean_data_str.split(':')
        value = value.strip()
        cleaned_data['UPC'] = value

        data_str = raw_data.get('TCIN')
        clean_data_str = data_str.replace('\\', '').replace('"', '')
        key, value = clean_data_str.split(':')
        cleaned_data['TCIN'] = value

        return cleaned_data
