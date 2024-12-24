from arsbot.utils.text_table import TextTable


def test_text_table():
    table = TextTable()

    table.set_header("WIP AutoMod Stats")
    table.set_footer("End of Stats")

    table.add_key_value("action", "approved")
    table.add_key_value("total", "43")
    table.add_key_value("catch_%", "97.67")
    table.add_key_value("not_as_spam", "42")
    table.add_key_value("as_spam", "1")
    table.add_key_value("has_link", "1")
    table.add_key_value("has_non_ascii", "0")
    table.add_key_value("has_all", "0")

    message = table.str()

    expected = """
```
==============================

      WIP AutoMod Stats

   action:         approved
   total:          43
   catch_%:        97.67
   not_as_spam:    42
   as_spam:        1
   has_link:       1
   has_non_ascii:  0
   has_all:        0

         End of Stats

==============================
```
"""[1:-1]

    assert message == expected


def test_text_table_2():
    table = TextTable()

    table.set_header("AutoMod Stats")
    table.set_footer("End of Stats")

    table.add_key_value("action", "approved_____________")
    table.add_key_value("total", "43")

    message = table.str()

    expected = """
```
==============================

        AutoMod Stats

action:  approved_____________
total:   43

         End of Stats

==============================
```
"""[1:-1]

    assert message == expected


def test_text_table_3():
    table = TextTable()

    table.set_header("Connected")
    table.set_footer("End of Info")

    table.add_key_value("action", "approved_____abcdefghijklmnopqrstuvwxyz123456789")
    table.add_key_value("total", "43")
    table.add_key_value("catch_%", "97.67")
    table.add_key_value("not_as_spam", "42")
    table.add_key_value("as_spam", "1")
    table.add_key_value("has_link", "1")
    table.add_key_value("has_non_ascii", "0")
    table.add_key_value("has_all", "0")

    message = table.str()

    expected = """
```
======================================================

                      Connected

                 action:         approved_____abcdefgh
ijklmnopqrstuvwxyz123456789

                 total:          43
                 catch_%:        97.67
                 not_as_spam:    42
                 as_spam:        1
                 has_link:       1
                 has_non_ascii:  0
                 has_all:        0

                     End of Info

======================================================
```
"""[1:-1]

    assert message == expected


def test_text_table_4():
    table = TextTable()

    table.set_header("Connected")
    table.set_footer("End of Info")

    table.add_key_value("action", "approved_____abcdefghijklmnopqrstuvwxyz")
    table.add_key_value("total", "43")
    table.add_key_value("catch_%", "97.67")
    table.add_key_value("not_as_spam", "42")
    table.add_key_value("as_spam", "1")
    table.add_key_value("has_link", "1")
    table.add_key_value("has_non_ascii", "0")
    table.add_key_value("has_all", "0")

    message = table.str()

    expected = """
```
=============================================

                  Connected

            action:         approved_____abcd
efghijklmnopqrstuvwxyz

            total:          43
            catch_%:        97.67
            not_as_spam:    42
            as_spam:        1
            has_link:       1
            has_non_ascii:  0
            has_all:        0

                 End of Info

=============================================
```
"""[1:-1]

    assert message == expected


def test_text_table_5():
    table = TextTable()

    table.set_header("Connected")
    table.set_footer("End of Info")

    table.add_key_value("action", "approved_")
    table.add_key_value("total", "43")
    table.add_key_value("catch_%", "97.67")
    table.add_key_value("not_as_spam", "42")
    table.add_key_value("as_spam", "1")
    table.add_key_value("has_link", "1")
    table.add_key_value("has_non_ascii", "0")
    table.add_key_value("has_all", "0")

    message = table.str()

    expected = """
```
==============================

          Connected

   action:         approved_
   total:          43
   catch_%:        97.67
   not_as_spam:    42
   as_spam:        1
   has_link:       1
   has_non_ascii:  0
   has_all:        0

         End of Info

==============================
```
"""[1:-1]

    assert message == expected
