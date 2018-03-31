import click
import math
import ntpath
import taglib
import struct
import sys
import wave

from AESCipherHelper import encrypt, decrypt
from HashHelper import sha256_hash


@click.group()
def cli():
    pass


@click.command()
@click.argument("file_to_hide", type=click.Path(exists=True))
@click.argument("audio_file_for_hiding", type=click.Path(exists=True))
@click.argument("passphrase")
def hide(file_to_hide, audio_file_for_hiding, passphrase):

    sound = wave.open(audio_file_for_hiding, "r")

    params = sound.getparams()
    num_channels = sound.getnchannels()
    sample_width = sound.getsampwidth()
    num_frames = sound.getnframes()
    num_samples = num_frames * num_channels

    input_data = open(file_to_hide, "rb").read()
    hash_input_data = sha256_hash(input_data)

    input_data = encrypt(input_data.decode(), passphrase)

    # We can hide up to num_lsb bits in each sample of the sound file
    filesize = len(input_data)
    num_lsb = math.ceil(filesize * 8 / num_samples)
    if (num_lsb > 4):
        raise ValueError("Input file too large to hide, "
                         "max byte to hide is {}"
                         .format((num_samples * num_lsb) // 8))

    if (sample_width == 1):  # samples are unsigned 8-bit integers
        fmt = "{}B".format(num_samples)
        # Used to set the least significant num_lsb bits of an integer to zero
        mask = (1 << 8) - (1 << num_lsb)
        # The least possible value for a sample in the sound file is actually
        # zero, but we don't skip any samples for 8 bit depth wav files.
        min_sample = -(1 << 8)
    elif (sample_width == 2):  # samples are signed 16-bit integers
        fmt = "{}h".format(num_samples)
        # Used to set the least significant num_lsb bits of an integer to zero
        mask = (1 << 15) - (1 << num_lsb)
        # The least possible value for a sample in the sound file
        min_sample = -(1 << 15)
    else:
        # Python's wave module doesn't support higher sample widths
        raise ValueError("File has an unsupported bit-depth")

    # Put all the samples from the sound file into a list
    raw_data = list(struct.unpack(fmt, sound.readframes(num_frames)))
    sound.close()

    # The number of bits we've processed from the input file
    data_index = 0
    sound_index = 0

    # values will hold the altered sound data
    values = []
    buffer = 0
    buffer_length = 0
    done = False

    while(not done):
        while (buffer_length < num_lsb and data_index // 8 < len(input_data)):
            # If we don't have enough data in the buffer, add the
            # rest of the next byte from the file to it.
            buffer += (input_data[data_index // 8] >> (data_index % 8)
                       ) << buffer_length
            bits_added = 8 - (data_index % 8)
            buffer_length += bits_added
            data_index += bits_added

        # Retrieve the next num_lsb bits from the buffer for use later
        current_data = buffer % (1 << num_lsb)
        buffer >>= num_lsb
        buffer_length -= num_lsb

        while (sound_index < len(raw_data) and
               raw_data[sound_index] == min_sample):
            # If the next sample from the sound file is the smallest possible
            # value, we skip it. Changing the LSB of such a value could cause
            # an overflow and drastically change the sample in the output.
            values.append(struct.pack(fmt[-1], raw_data[sound_index]))
            sound_index += 1

        if (sound_index < len(raw_data)):
            current_sample = raw_data[sound_index]
            sound_index += 1

            sign = 1
            if (current_sample < 0):
                # We alter the LSBs of the absolute value of the sample to
                # avoid problems with two's complement. This also avoids
                # changing a sample to the smallest possible value, which we
                # would skip when attempting to recover data.
                current_sample = -current_sample
                sign = -1

            # Bitwise AND with mask turns the num_lsb least significant bits
            # of current_sample to zero. Bitwise OR with current_data replaces
            # these least significant bits with the next num_lsb bits of data.
            altered_sample = sign * ((current_sample & mask) | current_data)

            values.append(struct.pack(fmt[-1], altered_sample))

        if (data_index // 8 >= len(input_data) and buffer_length <= 0):
            done = True

    while(sound_index < len(raw_data)):
        # At this point, there's no more data to hide. So we append the rest of
        # the samples from the original sound file.
        values.append(struct.pack(fmt[-1], raw_data[sound_index]))
        sound_index += 1

    sound_steg = wave.open("output.wav", "w")
    sound_steg.setparams(params)
    sound_steg.writeframes(b"".join(values))
    sound_steg.close()

    output_song = taglib.File("output.wav")
    output_song.tags["STEGO"] = "1"
    output_song.tags["STEGO_SIZE"] = str(filesize)
    output_song.tags["STEGO_CONTENT_SHA256"] = hash_input_data
    output_song.tags["STEGO_FILE_NAME"] = ntpath.basename(file_to_hide)
    output_song.tags["STEGO_LSB"] = str(num_lsb)
    output_song.save()


@click.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.argument("passphrase")
def retrieve(audio_file, passphrase):
    # Recover data from the file at sound_path to the file at output_path

    input_song = taglib.File(audio_file)
    if (not int(input_song.tags["STEGO"][0])):
        raise ValueError("No file is hidden inside")

    file_name = input_song.tags["STEGO_FILE_NAME"][0]
    bytes_to_recover = int(input_song.tags["STEGO_SIZE"][0])
    content_sha256 = input_song.tags["STEGO_CONTENT_SHA256"][0]
    num_lsb = int(input_song.tags["STEGO_LSB"][0])

    input_song.save()

    sound = wave.open(audio_file, "r")

    num_channels = sound.getnchannels()
    sample_width = sound.getsampwidth()
    num_frames = sound.getnframes()
    num_samples = num_frames * num_channels

    if (sample_width == 1):  # samples are unsigned 8-bit integers
        fmt = "{}B".format(num_samples)
        # The least possible value for a sample in the sound file is actually
        # zero, but we don't skip any samples for 8 bit depth wav files.
        min_sample = -(1 << 8)
    elif (sample_width == 2):  # samples are signed 16-bit integers
        fmt = "{}h".format(num_samples)
        # The least possible value for a sample in the sound file
        min_sample = -(1 << 15)
    else:
        # Python's wave module doesn't support higher sample widths
        raise ValueError("File has an unsupported bit-depth")

    # Put all the samples from the sound file into a list
    raw_data = list(struct.unpack(fmt, sound.readframes(num_frames)))
    # Used to extract the least significant num_lsb bits of an integer
    mask = (1 << num_lsb) - 1
    output_file = open(file_name, "wb+")

    data = bytearray()
    sound_index = 0
    buffer = 0
    buffer_length = 0

    while (bytes_to_recover > 0):

        next_sample = raw_data[sound_index]
        if (next_sample != min_sample):
            # Since we skipped samples with the minimum possible value when
            # hiding data, we do the same here.
            buffer += (abs(next_sample) & mask) << buffer_length
            buffer_length += num_lsb
        sound_index += 1

        while (buffer_length >= 8 and bytes_to_recover > 0):
            # If we have more than a byte in the buffer, add it to data
            # and decrement the number of bytes left to recover.
            current_data = buffer % (1 << 8)
            buffer >>= 8
            buffer_length -= 8
            data += struct.pack('1B', current_data)
            bytes_to_recover -= 1

    data = decrypt(bytes(data), passphrase)

    if (not (sha256_hash(data) == content_sha256)):
        raise ValueError("Wrong passphrase")

    output_file.write(data)
    output_file.close()


cli.add_command(hide)
cli.add_command(retrieve)

if __name__ == '__main__':
    cli()
