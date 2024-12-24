import math
import typing as t


class TextTable:
    def __init__(self):
        self._header = ""
        self._footer = ""
        self._padding_character = "="
        self._key_values = []
        self._max_key_len = 0
        self._max_value_len = 0
        self._max_key_value_len = 0

    def set_header(self, text: str) -> None:
        self._header = text

    def set_footer(self, text: str) -> None:
        self._footer = text

    def add_key_value(self, key: str, value: t.Any) -> None:
        if len(key) > self._max_key_len:
            self._max_key_len = len(key)

        value_str = str(value)
        if len(value_str) > self._max_value_len:
            self._max_value_len = len(value_str)

        if len(key) + len(value_str) > self._max_key_value_len:
            self._max_key_value_len = len(key) + len(value_str)

        self._key_values.append((key, value_str))

    @property
    def _key_value_padding_count(self):
        key_value_padding_count = None

        for key, value in self._key_values:
            key_value_space_count = self._max_key_len - len(key) + 2
            this_padding = math.floor(
                (
                    self._padding_count
                    - (
                        min(len(key), self._max_key_len)
                        + min(len(value), self._max_value_len)
                        + key_value_space_count
                    )
                )
                / 2
            )

            if this_padding < 0:
                continue

            if key_value_padding_count is None or (
                (this_padding < key_value_padding_count) and (this_padding > 0)
            ):
                key_value_padding_count = this_padding
                # assert key_value_padding_count != 0

        assert key_value_padding_count is not None

        return key_value_padding_count

    @property
    def _padding_count(self):
        min_padding_size = 30
        max_padding_size = 56

        padding_count = len(self._header)

        if len(self._footer) > padding_count:
            padding_count = len(self._footer)

        if self._max_key_value_len > padding_count:
            padding_count = self._max_key_value_len

        if padding_count > max_padding_size:
            padding_count = max_padding_size

        if padding_count < min_padding_size:
            padding_count = min_padding_size

        return padding_count

    def str(self) -> str:
        messages = []

        # assert self._padding_count == 30, self._padding_count

        header_padding_count = math.floor((self._padding_count - len(self._header)) / 2)
        # assert header_padding_count == 6, header_padding_count
        header_padding = " " * header_padding_count

        footer_padding_count = math.floor((self._padding_count - len(self._footer)) / 2)
        # assert footer_padding_count == 9, footer_padding_count
        footer_padding = " " * footer_padding_count

        padding = self._padding_character * self._padding_count

        messages.append("```")
        messages.append(padding)
        messages.append("")
        messages.append(f"{header_padding}{self._header}")
        messages.append("")

        for key, value in self._key_values:
            key_value_space_count = self._max_key_len - len(key) + 2
            key_value_space = " " * key_value_space_count

            runs_over_with_value = False
            if len(key) + key_value_space_count + 1 + len(value) > self._padding_count:
                runs_over_with_value = True

            # assert (
            #     key_value_padding_count == 3
            # ), f"{key_value_padding_count}{key}:{key_value_space}{value}"
            key_value_padding = " " * self._key_value_padding_count

            if runs_over_with_value:
                value_offset = 0
                message_to_add = f"{key_value_padding}{key}:"

                if (
                    key_space_count := len(message_to_add) + key_value_space_count
                ) < self._padding_count:
                    value_offset = self._padding_count - key_space_count
                    message_to_add += f"{key_value_space}{value[0:value_offset]}"

                messages.append(message_to_add)

                value_line_count = math.ceil(
                    len(value[value_offset:]) / self._padding_count
                )
                for value_line_index in range(0, value_line_count + 1):
                    message_to_add = value[
                        value_offset
                        + (self._padding_count * value_line_index) : value_offset
                        + (self._padding_count * (value_line_index + 1))
                    ]
                    messages.append(message_to_add)
            else:
                message_to_add = f"{key_value_padding}{key}:{key_value_space}{value}"
                messages.append(message_to_add)

        messages.append("")
        messages.append(f"{footer_padding}{self._footer}")
        messages.append("")
        messages.append(padding)
        messages.append("```")

        return "\n".join(messages)
