from common import IdCodeZT, IdIntsT, IdStrT, IdSigsT, IdCodeT, IdCountsT, IdLzjdT, IdFloatT
import hashes.ppdeep_mod as _ppdeep_mod
import hashes.ppdeep as _ppdeep
import ssdeep as _ssdeep
import hashes.ncd, hashes.bz
from hashes.jump import hash as _jumpHash
from contract.fourbytes import signatures
import functools, pyLZJD
from typing import List

def ppdeep_mod(codes: List[IdCodeT]) -> List[IdStrT]:
  return [IdStrT(id, _ppdeep_mod.hash(code)) for id, code in codes]

def ppdeep(codes: List[IdCodeT]) -> List[IdStrT]:
  return [IdStrT(id, _ppdeep.hash(code)) for id, code in codes]

def ssdeep(codes: List[IdCodeT]) -> List[IdStrT]:
  return [IdStrT(id, _ssdeep.hash(code)) for id, code in codes]

def fourbytes(codes: List[IdCodeT]) -> List[IdSigsT]:
  return [IdSigsT(id, signatures(code)) for id, code in codes]

def byteBag(codes: List[IdCodeT]) -> List[IdCountsT]:
  def reducer(counts, b):
    counts[b] = counts.get(b, 0) + 1
    return counts

  return [
    IdCountsT(id, functools.reduce(reducer, code, {}))
    for id, code in codes]

def lzjd1(
  codes: List[IdCodeT], hash_size = 1024, mode = None,
  processes = -1, false_seen_prob = 0, seed = None
):
  return [
    IdLzjdT(id, pyLZJD.digest(code, hash_size, mode, processes, false_seen_prob, seed))
    for id, code, in codes]

def size(codes: List[IdCodeT]) -> List[IdFloatT]:
  return [ IdFloatT(id, len(code)) for id, code in codes ]

def jumpHash(codes: List[IdCodeT]) -> List[IdStrT]:
  return [IdStrT(id, _jumpHash(code)) for id, code, in codes]

def ncd(codes: List[IdCodeT]) -> List[IdCodeZT]:
  return [IdCodeZT(id, code, hashes.ncd.Z(code)) for id, code in codes]

def bzFixedLen(codes: List[IdCodeT], chunkLen=200, chunkRes=8) -> List[IdStrT]:
  return [
    IdStrT(id, hashes.bz.hashFixedLen(code, chunkLen=chunkLen, chunkRes=chunkRes))
    for id, code in codes]

def bzJumpi(codes: List[IdCodeT], chunkRes=8) -> List[IdStrT]:
  return [
    IdStrT(id, hashes.bz.hashJumpi(code, chunkRes=chunkRes))
    for id, code in codes]
