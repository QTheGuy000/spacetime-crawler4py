# O(n) time: scans each character once to build lowercase alphanumeric tokens.
def tokenize_text(text):
    """Returns lowercase alphanumeric tokens from a string, skipping non-ASCII."""
    tokens = []
    current = []

    for ch in text:
        if ord(ch) > 127:
            if current:
                tokens.append("".join(current).lower())
                current = []
            continue

        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current).lower())
                current = []

    if current:
        tokens.append("".join(current).lower())

    return tokens