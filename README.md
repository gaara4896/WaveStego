# WaveStego

A steganography implementation for wave file type

## Usage

```
python WaveStego.py <COMMAND> [ARGS]

Commands:
  hide
  retrieve
```

### Hide

```
python WaveStego.py hide <FILE_TO_HIDE> <AUDIO_FILE_FOR_HIDING> <PASSPHRASE>
```

1. FILE_TO_HIDE is the file you want to hide inside .wav audio file

1. AUDIO_FILE_FOR_HIDING is the original audio file you want to hide

1. PASSPHRASE is the password, required during retrieve

After hiding, it will generate a file call `output.wav`, which is the audio file with hidden data inside

*Sample*

```
python WaveStego.py hide test.txt drop.wav abc123
```

### Retrieve

```
python WaveStego.py retrieve <AUDIO_FILE> <PASSPHRASE>
```

1. AUDIO_FILE is the input file

1. PASSPHRASE is the password that used to hide file

If the audio file do not contain any file or wrong password user shall get `ValueError`

*Sample*

```
python WaveStego.py retrieve output.wav abc123
```