from bakery import assert_equal
from dataclasses import dataclass
from drafter import *
from PIL import Image as PIL_Image
import io

header_length = 3
max_message_length = 999
green_channel = 1
copyright_message = "Copyright 2026"
 
 
@dataclass
class Record:
    step_message: str
    mode: str
 
 
@dataclass
class State:
    message: str
    image_data: PIL_Image.Image
    output: str
    message_history: list[Record]
 

@route
def index(state: State) -> Page:
    """
    The home page where you can click a button to encrypt, decrypt, and open the help page.
    """
    return Page(state, [
        Header("Steganography App", 2),
        Paragraph("Hide any message inside a PNG image file."),
        Button("Encrypt your message.", encrypt_text),
        Button("Decrypt your message.", decrypt_text),
        Button("Help Page", help_page),
    ])
 
 
@route
def encrypt_text(state: State) -> Page:
    """
    The encryption page where the user is prompted to upload an image and enter a secret message
    or phrase to encrypt.
    """
    return Page(state, [
        Header("Encrypt a Message", 2),
        Paragraph("Upload an image file to encrypt:"),
        FileUpload("image_file", accept="image/png"),
        Paragraph("Short label for help page:"),
        TextBox("label"),
        Paragraph("Secret message you want to hide:"),
        TextArea("message"),
        Paragraph("Do you want to add a copyright message to your encrypted message?"),
        CheckBox("add_copyright"),
        Button("Hide Message", do_encrypt),
        Button("Back to Home", index),
    ])

@route
def do_encrypt(state: State, image_file: bytes, label: str, message: str,
               add_copyright: bool) -> Page:
    """
    Hides the message in the image and records each step as history under the help page
    """
    if not image_file:
        return error_page(state, "No image was uploaded please upload an image file.")
    if message == "":
        return error_page(state, "No message was entered, please try again.")
    if not message.isascii():
        return error_page(state, "Your message requires only plain ASCII characters, try again.")

    if add_copyright:
        message = copyright_message + message

    image = open_png(image_file)
    if not message_fit(image, message):
        return error_page(state, "Your message is to long for the image, please write a message under 999 characters.")
    if label == "":
        label = "untitled"
    full_message = prepend_header(message)
    binary_string = message_to_binary(full_message)
    state.message = message
    state.image_data = hide_bits(image, binary_string)
    state.output = "Message hidden successfully."
    step_number = len(state.message_history) + 1
    step_message = step_history(step_number, "encoded", label)
    state.message_history.append(Record(step_message, "encoded"))
    return result_page(state)


@route
def decrypt_text(state: State) -> Page:
    """
    The decryption page to upload an image that has a hidden phrase or message.
    """
    return Page(state, [
        Header("Decrypt a Message", 2),
        Paragraph("Upload the image file with the hidden message:"),
        FileUpload("image_file", accept="image/png"),
        Button("Reveal Message", do_decrypt),
        Button("Back to Home", index),
    ])


@route
def do_decrypt(state: State, image_file: bytes) -> Page:
    """
    Decrypts the hidden message from the encoded image file and records each step in the help/history tab
    """
    if not image_file:
        return error_page(state, "No image was uploaded, please reupload an image")

    image = open_png(image_file)
    channel_values = get_color_values(image, green_channel)
    decoded_message = get_encoded_message(channel_values)
    if decoded_message == "":
        return error_page(state, "No hidden message was found in the image, please try again.")

    state.message = decoded_message
    state.image_data = image
    state.output = "Hidden message: \"" + decoded_message + "\""
    step_number = len(state.message_history) + 1
    step_message = step_history(step_number, "decoded", decoded_message)
    state.message_history.append(Record(step_message, "decoded"))
    return result_page(state)


@route
def result_page(state: State) -> Page:
    """
    Shows the output of the most recent encryption or decryption and the image that it was related too.
    """
    if len(state.message_history) == 0:
        return error_page(state, "There is no result yet.")
    content = [
        Header("Result", 2),
        Paragraph(state.output),
        Image(state.image_data),
    ]
    last_record = state.message_history[-1]
    if last_record.mode == "encoded":
        content.append(Download("Download the encoded image", "encoded_image.png", state.image_data))
                                
    content.append(Button("Back to Home", index))
    return Page(state, content)


@route
def error_page(state: State, error_message: str) -> Page:
    """
    Shows what went wrong and sends the user back to the index(home)
    """
    return Page(state, [
        Header("Something went wrong", 2),
        Paragraph(error_message),
        Button("Back to Home", index),
    ])


@route
def help_page(state: State) -> Page:
    """
    Shows instructions for the app and the history of every encryption and decryption step
    """
    encoded_total = record_counter(state.message_history, "encoded")
    decoded_total = record_counter(state.message_history, "decoded")
    content = [
        Header("How to use the Steganography App", 2),
        Header("Encryption", 3),
        NumberedList([
            "Click the encrypt message to encrypt your message by entering your message.",
            "Add a copyright message if needed.",
            "Click the hide message button and download your encrypted image file.",
        ]),
        Header("Decryption", 3),
        NumberedList([
            "Click decrypt a message and upload your encrypted image file.",
            "Click to reveal message",
        ]),
        Header("Message History", 2),
        Paragraph("Encoded: " + str(encoded_total) + " | Decoded: " + str(decoded_total)),
    ]
    if len(state.message_history) == 0:
        content.append(Paragraph("No steps yet..."))
    for line in history_records(state.message_history):
        content.append(Paragraph(line))
    content.append(Button("Back to Home", index))
    return Page(state, content)



def open_png(image_file: bytes) -> PIL_Image.Image:
    """
    Turns the uploaded file to bytes using the RGB image
    """
    return PIL_Image.open(io.BytesIO(image_file)).convert("RGB")


def message_fit(image: PIL_Image.Image, message: str) -> bool:
    """
    Checks if the header and message fit into the image. It's required to have 8 bits too for each pixel
    to be hiden. Nothing can be longer than 999 characters.
    """
    if len(message) > max_message_length:
        return False
    width, height = image.size
    bits_needed = (header_length + len(message)) * 8
    return bits_needed <= width * height


def step_history(step: int, mode: str, label: str) -> str:
    """
    Builds each step for the history tab. Keeps adding each encoded message and the label given.
    """
    return "Step " + str(step) + " (" + mode + "): " + label


def record_counter(records: list[Record], mode: str) -> int:
    """
    Counts how many records have the have each given mode
    """
    total = 0
    for record in records:
        if record.mode == mode:
            total = total + 1
    return total


def history_records(records: list[Record]) -> list[str]:
    """
    returns each step message of each record in order
    """
    lines = []
    for record in records:
        lines.append(record.step_message)
    return lines


def prepend_header(user_message: str) -> str:
    """
    Puts a three digit header in front of the message and the header becomes the number
    of characters in the message
    """
    message_length = len(user_message)
    header = str(message_length).zfill(header_length)
    return header + user_message


def message_to_binary(message: str) -> str:
    """
    Converts each character to ASCII characters using ord() and formats each number into 8 bits.
    """
    result = ""
    for character in message:
        ascii_number = ord(character)
        bits = format(ascii_number, '08b')
        result = result + bits
    return result


def new_color_value(original_value: int, bit_to_hide: str) -> int:
    """
    Changes a color value by at most 1 so its even/odd LSB matches the bit being hidden
    """
    if bit_to_hide == "1":
        if original_value % 2 == 0:
            return original_value + 1
        else:
            return original_value
    else:
        if original_value % 2 == 1:
            return original_value - 1
        else:
            return original_value


def hide_bits(original_image: PIL_Image.Image, binary_string: str) -> PIL_Image.Image:
    """
    Hides one bit per pixel in the green channel only. Than it goes column by column through x
    on the outside and y on the inside and returns that copy. This means the original image is not
    alterred in any way.
    """
    new_image = original_image.copy().convert("RGB")
    width, height = new_image.size

    x = 0
    y = 0
    for bit in binary_string:
        red, green, blue = new_image.getpixel((x, y))
        new_green = new_color_value(green, bit)
        new_image.putpixel((x, y), (red, new_green, blue))

        y += 1
        if y == height:
            y = 0
            x += 1

    return new_image


def even_or_odd_bit(number: int) -> str:
    """
    Returns 1 if the number is odd and 0 if the number is even
    """
    if number % 2 != 0:
        return "1"
    else:
        return "0"


def decode_single_char(channel_values: list[int]) -> str:
    """
    Turns exactly 8 color values into one character by reading the evne or odd bit of each character
    If there isn't exactly 8 values it returns ""
    """
    if len(channel_values) != 8:
        return ""
    bits = ""
    for value in channel_values:
        bits = bits + even_or_odd_bit(value)
    ascii_number = int(bits, 2)
    return chr(ascii_number)


def decode_chars(channel_values: list[int], num_chars: int) -> str | None:
    """
    Decodes num_chars characters 8 color values at a time and returns None if the number does not
    match exactly 8 * num_chars
    """
    expected_length = 8 * num_chars
    if expected_length != len(channel_values):
        return None

    result = ""
    for start in range(0, len(channel_values), 8):
        group = channel_values[start: start + 8]
        result = result + decode_single_char(group)
    return result


def messages_lengths(channel_values: list[int], num_header_chars: int) -> int:
    """
    Decodes the header and returns it as a number. Than returns 0 if there are too few values or
    the header isn't all digits.
    """
    header_bits = 8 * num_header_chars
    if header_bits > len(channel_values):
        return 0

    header = decode_chars(channel_values[:header_bits], num_header_chars)
    if not header.isdigit():
        return 0
    return int(header)


def get_encoded_message(channel_values: list[int]) -> str:
    """
    Reads the header to find the message length and then decodes that many characters after the header.
    """
    header_bits = 8 * header_length
    message_length = messages_lengths(channel_values[:header_bits], header_length)
    if message_length == 0:
        return ""

    message_values = channel_values[header_bits: header_bits + message_length * 8]
    decoded_message = decode_chars(message_values, message_length)
    if decoded_message is None:
        return ""
    return decoded_message


def get_color_values(image: PIL_Image.Image, channel_number: int) -> list[int]:
    """
    Returns the value of one colo channel for each pixel column by column. X on the outside
    and y on the inside to match the order of hide_bits
    """
    width, height = image.size
    color_values = []
    for x in range(width):
        for y in range(height):
            pixel = image.getpixel((x, y))
            color_values.append(pixel[channel_number])
    return color_values


def image_to_png(image: PIL_Image.Image) -> bytes:
    """
    Saves an image as a PNG image only
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()



assert_equal(new_color_value(100, "1"), 101)
assert_equal(new_color_value(77, "1"), 77)
assert_equal(new_color_value(55, "0"), 54)
assert_equal(new_color_value(120, "0"), 120)
assert_equal(message_to_binary("Hi"), "0100100001101001")
assert_equal(message_to_binary("058"), "001100000011010100111000")
assert_equal(message_to_binary("Hello"), "0100100001100101011011000110110001101111")
assert_equal(message_to_binary("A"), "01000001")
assert_equal(prepend_header("Heyyo"), "005Heyyo")
assert_equal(prepend_header("S o S"), "005S o S")
assert_equal(prepend_header("67"), "00267")
assert_equal(prepend_header("hello"), "005hello")
assert_equal(even_or_odd_bit(5), "1")
assert_equal(even_or_odd_bit(6), "0")
assert_equal(even_or_odd_bit(1), "1")
assert_equal(even_or_odd_bit(100), "0")
assert_equal(decode_single_char([46, 47, 46, 46, 47, 44, 46, 44]), "H")
assert_equal(decode_single_char([46, 47, 46, 46, 47, 48, 48, 44]), "H")
assert_equal(decode_single_char([46, 47, 46, 46, 46, 44, 46, 44]), "@")
assert_equal(decode_single_char([46, 47]), "")
assert_equal(decode_chars([0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1], 2), "25")
assert_equal(decode_chars([], 0), "")
assert_equal(decode_chars([0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1], 2), None)
assert_equal(messages_lengths(
    [20, 254, 45, 95, 40, 90, 20, 40, 200, 254, 45, 95, 40, 95, 20, 45,
     220, 250, 45, 95, 48, 95, 24, 44], 3), 54)
assert_equal(messages_lengths(
    [20, 254, 45, 95, 40, 99, 27, 52, 200, 254, 45, 95, 40, 95, 20, 45,
     220, 250, 45, 95, 48, 95, 24, 44], 3), 654)
assert_equal(messages_lengths([20, 254, 45], 3), 0)
assert_equal(get_encoded_message([
    254, 254, 255, 255, 254, 254, 254, 254,
    254, 254, 255, 255, 254, 254, 254, 254,
    254, 254, 255, 255, 254, 254, 255, 254,
    254, 255, 254, 254, 255, 254, 254, 254,
    254, 255, 255, 254, 255, 254, 254, 255,
    254, 254, 254, 254, 254, 254, 254, 254,
    254, 254, 254, 254, 254, 254, 254, 254,
    254, 254, 254, 254, 254, 254, 254, 254,
    254, 254, 254, 254, 254, 254, 254, 254,
    254, 254, 254, 254, 254, 254, 254, 254,
    252]), "Hi")
assert_equal(get_encoded_message([144, 167, 140]), "")
testimg1 = PIL_Image.new("RGB", (12, 12), (144, 144, 244))
assert_equal(get_color_values(testimg1, 1), [144] * 144)
hiddenimg1 = hide_bits(testimg1, message_to_binary(prepend_header("yo")))
assert_equal(testimg1.getpixel((0, 0)), (144, 144, 244))
assert_equal(get_encoded_message(get_color_values(hiddenimg1, 1)), "yo")
assert_equal(get_color_values(hiddenimg1, 0), [144] * 144)
assert_equal(hide_bits(testimg1, "1").getpixel((0, 0)), (144, 145, 244))
assert_equal(message_fit(testimg1, "yo"), True)
assert_equal(message_fit(testimg1, "19956432"), True)
assert_equal(message_fit(testimg1, "1999999999"), True)
assert_equal(message_fit(PIL_Image.new("RGB", (1000, 1000)), "a" * 1000), False)
assert_equal(step_history(1, "encoded", "heyy"), "Step 1 (encoded): heyy")
records1 = [Record("Step 1 (encoded): heyy", "encoded"),
                Record("Step 2 (decoded): wassup", "decoded"),
                Record("Step 3 (encoded): hello", "encoded")]
assert_equal(record_counter(records1, "encoded"), 2)
assert_equal(record_counter(records1, "decoded"), 1)
assert_equal(record_counter([], "encoded"), 0)
assert_equal(history_records(records1), ["Step 1 (encoded): heyy",
                                           "Step 2 (decoded): wassup",
                                           "Step 3 (encoded): hello"])
assert_equal(history_records([]), [])
assert_equal(open_png(image_to_png(testimg1)).size, (12, 12))
pngbits1 = image_to_png(PIL_Image.new("RGB", (20, 20), (50, 60, 70)))
assert_equal(index(State("", None, "", [])).content[0],
             Header("Steganography App", 2))
assert_equal(encrypt_text(State("", None, "", [])).content[0],
             Header("Encrypt a Message", 2))
assert_equal(decrypt_text(State("", None, "", [])).content[0],
             Header("Decrypt a Message", 2))
assert_equal(error_page(State("", None, "", []), "wrong").content[1], Paragraph("wrong"))
assert_equal(do_encrypt(State("", None, "", []), b"", "yes", "hey", False).content[1],
             Paragraph("No image was uploaded please upload an image file."))
assert_equal(do_encrypt(State("", None, "", []), pngbits1, "yes", "", False).content[1],
             Paragraph("No message was entered, please try again."))
assert_equal(do_encrypt(State("", None, "", []), pngbits1, "e", "é",
                        False).content[1],
             Paragraph("Your message requires only plain ASCII characters, try again."))
assert_equal(do_encrypt(State("", None, "", []), pngbits1, "yes", "a" * 100,
                        False).content[1],
             Paragraph("Your message is to long for the image, "
                       "please write a message under 999 characters."))
encrypt_state = State("", None, "", [])
encrypt_page_result = do_encrypt(encrypt_state, pngbits1, "yes", "hey", False)
assert_equal(encrypt_page_result.state.message, "hey")
assert_equal(encrypt_page_result.state.output,
             "Message hidden successfully.")
assert_equal(encrypt_page_result.state.message_history,
             [Record("Step 1 (encoded): yes", "encoded")])
assert_equal(get_encoded_message(
    get_color_values(encrypt_page_result.state.image_data, 1)), "hey")
assert_equal(encrypt_page_result.content[0], Header("Result", 2))
copyright_result = do_encrypt(State("", None, "", []), pngbits1, "art", "Hi", True)
assert_equal(copyright_result.state.message, copyright_message + "Hi")
assert_equal(get_encoded_message(
    get_color_values(copyright_result.state.image_data, 1)),
    copyright_message + "Hi")
assert_equal(do_decrypt(State("", None, "", []), b"").content[1],
             Paragraph("No image was uploaded, please reupload an image"))
assert_equal(do_decrypt(State("", None, "", []), pngbits1).content[1],
             Paragraph("No hidden message was found in the image, please try again."))
encoded_bytes = image_to_png(encrypt_page_result.state.image_data)
decrypt_page_result = do_decrypt(State("", None, "", []), encoded_bytes)
assert_equal(decrypt_page_result.state.message, "hey")
assert_equal(decrypt_page_result.state.output, "Hidden message: \"hey\"")
assert_equal(decrypt_page_result.state.message_history,
             [Record("Step 1 (decoded): hey", "decoded")])
assert_equal(result_page(State("", None, "", [])).content[1],
             Paragraph("There is no result yet."))
assert_equal(len(result_page(decrypt_page_result.state).content), 4)
assert_equal(len(result_page(encrypt_page_result.state).content), 5)
 
  
set_site_information(
    author="Brendan Richards",
    description="Use Steganography to carry a secret message or phrase, to either encode or decode the message from an image file using the least significant bit.",
    sources="Drafter Documentation, Crypto Corgi Project, BlockPy Dashboard",
    planning=["CS1 Final Project Plan.pdf", "CS1 Final Project Design 1.pdf"],
    links=["https://github.com/brenrich44/steganography-project"]
)



start_server(State("", None, "", []))


