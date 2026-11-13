"""역색인: keyword / author -> 커밋 hash 목록."""


class InvertedIndex:
    """검색할 때 모든 커밋을 순회(O(N))하지 않고, 딕셔너리 조회(평균 O(1))로
    후보 목록을 바로 가져온다.
    """

    def __init__(self):
        self.by_keyword = {}
        self.by_author = {}

    def add(self, commit):
        """커밋 생성 시 호출. 메시지를 공백으로 나누고 소문자로 바꿔 저장한다."""
        for token in set(commit.message.lower().split()):
            self.by_keyword.setdefault(token, []).append(commit.hash)
        self.by_author.setdefault(commit.author, []).append(commit.hash)

    def search_keyword(self, text):
        """키워드가 메시지에 포함된 커밋. 단어가 여러 개면 모두 포함된 커밋."""
        tokens = text.lower().split()
        if not tokens:
            return []
        result = self.by_keyword.get(tokens[0], [])
        for token in tokens[1:]:
            others = set(self.by_keyword.get(token, []))
            result = [h for h in result if h in others]
        return list(result)

    def search_author(self, name):
        """해당 작성자의 커밋 (이름은 대소문자 구분)."""
        return list(self.by_author.get(name, []))
