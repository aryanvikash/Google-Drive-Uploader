# This  Thing will only identify sent token :D


def is_token(token):
    token = token.split()[-1]
    TLEN = len(token)
    if TLEN == 62:
        if token[1] == "/":
            return True
        else:
            return False
    else:
        return False
