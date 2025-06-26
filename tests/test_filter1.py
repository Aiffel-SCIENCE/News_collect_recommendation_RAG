from src.filter1.filter1 import check_drop_word, check_drop_url


test_text = ["아이펠 아이젠 사이언스", "바보 똥강아지", "화이팅"]
test_url = ["www.google.com", "www.naver.com", "www.daum.net"]

for test_case in test_text:
    result = check_drop_word(test_case)
    print(f'Case: {test_case} => {"Drop" if result else "Pass"}')

for test_case in test_url:
    result = check_drop_url(test_case)
    print(f'Case: {test_case} => {"Drop" if result else "Pass"}')

