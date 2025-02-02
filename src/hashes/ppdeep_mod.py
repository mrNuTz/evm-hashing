#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
based on ppdeep

should behave identical to ssdeep except:
- no int rounding in score calculation : differentiate between exact match and close match
- no sequence stripping : hash with long strips of 'K' chunk-hashes become incomparable
- no common substring detection : makes many hashes incomparable
- option to use jaccard-index for scoring
- handle first chunk never triggered
'''

__title__ = 'ppdeep_mod'
__version__ = '20210318'
__author__ = 'Raphael Nußbaumer'

import os
from io import BytesIO

BLOCKSIZE_MIN = 3
SPAMSUM_LENGTH = 64

def _spamsum(stream, slen):
	STREAM_BUFF_SIZE = 8192
	HASH_PRIME = 0x01000193
	HASH_INIT = 0x28021967
	ROLL_WINDOW = 7
	B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

	roll_win = bytearray(ROLL_WINDOW)
	roll_h1 = int()
	roll_h2 = int()
	roll_h3 = int()
	roll_n = int()
	block_size = int()
	hash_string1 = str()
	hash_string2 = str()
	block_hash1 = int(HASH_INIT)
	block_hash2 = int(HASH_INIT)

	bs = BLOCKSIZE_MIN
	while (bs * SPAMSUM_LENGTH) < slen:
		bs = bs * 2
	block_size = bs

	while True:
		if block_size < BLOCKSIZE_MIN:
			raise RuntimeError('Calculated block size is too small')

		stream.seek(0)
		buf = stream.read(STREAM_BUFF_SIZE)
		while buf:
			for b in buf:
				block_hash1 = ((block_hash1 * HASH_PRIME) & 0xFFFFFFFF) ^ b
				block_hash2 = ((block_hash2 * HASH_PRIME) & 0xFFFFFFFF) ^ b

				roll_h2 = roll_h2 - roll_h1 + (ROLL_WINDOW * b)
				roll_h1 = roll_h1 + b - roll_win[roll_n % ROLL_WINDOW]
				roll_win[roll_n % ROLL_WINDOW] = b
				roll_n += 1
				roll_h3 = (roll_h3 << 5) & 0xFFFFFFFF
				roll_h3 ^= b

				rh = roll_h1 + roll_h2 + roll_h3

				if (rh % block_size) == (block_size - 1):
					if len(hash_string1) < (SPAMSUM_LENGTH - 1):
						hash_string1 += B64[block_hash1 % 64]
						block_hash1 = HASH_INIT
					if (rh % (block_size * 2)) == ((block_size * 2) - 1):
						if len(hash_string2) < ((SPAMSUM_LENGTH // 2) - 1):
							hash_string2 += B64[block_hash2 % 64]
							block_hash2 = HASH_INIT

			buf = stream.read(STREAM_BUFF_SIZE)

		if block_size > BLOCKSIZE_MIN and len(hash_string1) < (SPAMSUM_LENGTH // 2):
			block_size = (block_size // 2)

			roll_win = bytearray(ROLL_WINDOW)
			roll_h1 = roll_h2 = roll_h3 = int()
			roll_n = int()

			block_hash1 = block_hash2 = HASH_INIT
			hash_string1 = hash_string2 = str()
		else:
			rh = roll_h1 + roll_h2 + roll_h3
			if rh != 0:
				hash_string1 += B64[block_hash1 % 64]
				hash_string2 += B64[block_hash2 % 64]
			break

	if hash_string1 == '':
		hash_string1 += B64[block_hash1 % 64]
	if hash_string2 == '':
		hash_string2 += B64[block_hash2 % 64]

	return '{0}:{1}:{2}'.format(block_size, hash_string1, hash_string2)


def hash(buf):
	if isinstance(buf, bytes) or isinstance(buf, memoryview):
		pass
	elif isinstance(buf, str):
		buf = buf.encode()
	else:
		raise TypeError('Argument must be of bytes or string type, not %r' % type(buf))
	return _spamsum(BytesIO(buf), len(buf))


def hash_from_file(filename):
	if not isinstance(filename, str):
		raise TypeError('Argument must be of string type, not %r' % type(filename))
	if not os.path.isfile(filename):
		raise IOError('File not found')
	if not os.access(filename, os.R_OK):
		raise IOError('File is not readable')
	fsize = os.stat(filename).st_size
	return _spamsum(open(filename, 'rb'), fsize)


def _levenshtein(s, t):
	'''
	Implementation by Christopher P. Matthews
	'''
	if s == t: return 0
	elif len(s) == 0: return len(t)
	elif len(t) == 0: return len(s)
	v0 = [None] * (len(t) + 1)
	v1 = [None] * (len(t) + 1)
	for i in range(len(v0)):
		v0[i] = i
	for i in range(len(s)):
		v1[0] = i + 1
		for j in range(len(t)):
			cost = 0 if s[i] == t[j] else 1
			v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
		for j in range(len(v0)):
			v0[j] = v1[j]
	return v1[len(t)]

def _jaccard_index(list1, list2):
  a = set(list1)
  b = set(list2)
  aSize = len(a)
  bSize = len(b)
  intersectionSize = len(a.intersection(b))
  return intersectionSize / (aSize + bSize - intersectionSize)

class _RollState(object):
	ROLL_WINDOW = 7

	def __init__(self):
		self.win = bytearray(self.ROLL_WINDOW)
		self.h1 = int()
		self.h2 = int()
		self.h3 = int()
		self.n = int()

	def roll_hash(self, b):
		self.h2 = self.h2 - self.h1 + (self.ROLL_WINDOW * b)
		self.h1 = self.h1 + b - self.win[self.n % self.ROLL_WINDOW]
		self.win[self.n % self.ROLL_WINDOW] = b
		self.n += 1
		self.h3 = (self.h3 << 5) & 0xFFFFFFFF
		self.h3 ^= b
		return self.h1 + self.h2 + self.h3


def _score_strings(s1, s2, block_size, useJaccard=False):
	if useJaccard:
		return 100 * _jaccard_index(s1, s2)
	score = _levenshtein(s1, s2)
	score = 100 - 100 * score / (len(s1) + len(s2))
	score = min(score, block_size / BLOCKSIZE_MIN * min(len(s1), len(s2)))
	return score

def compare(hash1, hash2, useJaccard=False):
	if not (isinstance(hash1, str) and isinstance(hash2, str)):
		raise TypeError('Arguments must be of string type')
	try:
		hash1_bs, hash1_s1, hash1_s2 = hash1.split(':')
		hash2_bs, hash2_s1, hash2_s2 = hash2.split(':')
		hash1_bs = int(hash1_bs)
		hash2_bs = int(hash2_bs)
	except ValueError:
		raise ValueError('Invalid hash format') from None

	if hash1_bs != hash2_bs and hash1_bs != (hash2_bs * 2) and hash2_bs != (hash1_bs * 2):
		return 0

	if hash1_bs == hash2_bs and hash1_s1 == hash2_s1:
		return 100

	if hash1_bs == hash2_bs:
		score1 = _score_strings(hash1_s1, hash2_s1, hash1_bs, useJaccard)
		score2 = _score_strings(hash1_s2, hash2_s2, hash2_bs, useJaccard)
		score = max([score1, score2])
		return score
	elif hash1_bs == (hash2_bs * 2):
		score = _score_strings(hash1_s1, hash2_s2, hash1_bs, useJaccard)
		return score
	else:
		score = _score_strings(hash1_s2, hash2_s1, hash2_bs, useJaccard)
		return score
	return 0


if __name__ == '__main__':
	import sys
	if len(sys.argv) > 1:
		print(hash_from_file(sys.argv[1]))
	else:
		with open(0, 'rb') as f:
			print(hash(f.read()))
