import sys, os, time
from typing import Callable
sys.path.insert(1, 'src')
import write, plot
_runDir = os.path.dirname(os.path.abspath(__file__))
_outDir = _runDir + '/out'
write.setDir(_outDir)
plot.setDir(_outDir)

import pre, hash, similarity, util, test, opfilter
import pandas as pd
import datasets.smallGroupsByAbi as smallGroupsByAbi

(idToCode, idToMeta, nameToIds) = smallGroupsByAbi.load()

def byteBagJaccard(pairs):
  return similarity.byteBagJaccard(pairs, excludeZeros=True)
def highFOnly(codes):
  return pre.filterBytes(codes, opfilter.highFStatPred)
def highF0(codes):
  return pre.setBytesZero(codes, opfilter.highFStatPred)
def highFOnlyV2(codes):
  return pre.filterBytes(codes, opfilter.highFStatV2Pred)
def highF0V2(codes):
  return pre.setBytesZero(codes, opfilter.highFStatV2Pred)
def lzjd(codes):
  return hash.lzjd1(codes, hash_size=256, mode=None, false_seen_prob=0)
def bzJumpi4(codes):
  return hash.bzJumpi(codes, chunkRes=4)

def run(metaPredicate: Callable[[smallGroupsByAbi.Meta], bool], name: str):
  codes = [idToCode[id] for id, meta in idToMeta.items() if metaPredicate(meta)]

  print(name)
  print(f'groups: {set(idToMeta[id].name for id, code in codes)}')
  print(f'codes len: {len(codes)}')
  print('')

  preToCodes = {
    'raw': codes,
    'skeletons': util.concurrent(pre.skeleton)(codes),
    'fstSecSkel': util.concurrent(pre.firstSectionSkeleton)(codes),
  }
  preToCodes.update({
    'fStat': util.concurrent(highFOnly)(preToCodes['fstSecSkel']),
    'fStat0': util.concurrent(highF0)(preToCodes['fstSecSkel']),
    'fStatV2': util.concurrent(highFOnlyV2)(preToCodes['fstSecSkel']),
    'fStat0V2': util.concurrent(highF0V2)(preToCodes['fstSecSkel']),
  })

  hashToFunction = {
    'ssdeep': hash.ssdeep,
    'ppdeep': hash.ppdeep,
    'ppdeep_mod': hash.ppdeep_mod,
    'byteBag': hash.byteBag,
    'lzjd': lzjd,
    'bz': bzJumpi4,
    'jump': hash.jumpHash,
    'ncd': hash.ncd,
    'fourbytes': hash.fourbytes
  }

  methodToHashes = {
    (p, h): util.concurrent(hashToFunction[h])(preToCodes[p])
    for p in preToCodes.keys() for h in hashToFunction.keys()
  }

  methodToPairs = {
    method: util.allToAllPairs(hashes) for method, hashes in methodToHashes.items()
  }

  hashToCompareFunction = {
    'ssdeep': similarity.ssdeep,
    'ppdeep': similarity.ppdeep,
    'ppdeep_mod': similarity.ppdeep_mod,
    'byteBag': byteBagJaccard,
    'lzjd': similarity.lzjd,
    'bz': similarity.levenshtein,
    'jump': similarity.levenshtein,
    'ncd': similarity.ncd,
    'fourbytes': similarity.jaccardIndex
  }

  methodToComps = {}
  methodToTime = {}
  for (method, pairs) in methodToPairs.items():
    print('comparing ' + name + ' ' + ' '.join(method))
    start = time.time()
    methodToComps[method] = util.concurrent(hashToCompareFunction[method[1]])(pairs)
    elapsed = time.time() - start
    methodToTime[method] = elapsed
    print(f"{elapsed} sec")

  comps1 = tuple(util.fst(methodToComps.values()))

  columns = {
    'isInner': (idToMeta[id1].name == idToMeta[id2].name for id1, id2, val in comps1),
    'id1': (id1 for id1, id2, val in comps1),
    'id2': (id2 for id1, id2, val in comps1),
    'group1': (idToMeta[id1].name for id1, id2, val in comps1),
    'group2': (idToMeta[id2].name for id1, id2, val in comps1),
  }
  columns.update({
    ' '.join(method): (val for id1, id2, val in comps)
    for method, comps in methodToComps.items()
  })

  df = pd.DataFrame(columns)
  corr = df.corr(method='kendall')
  separations = test.separation(df)
  qDists = test.qDist(df)

  write.saveCsv(separations.items(), filename=name + ' separations.csv')
  write.saveCsv(qDists.items(), filename=name + ' qDists.csv')
  write.saveCsv(methodToTime.items(), filename=name + ' runtimes.csv')
  write.saveGml((idToMeta[id] for id, code in codes), df, filename=name + '.gml')
  write.saveStr(df.to_csv(), name + ' similarities.csv')
  write.saveStr(corr.to_csv(), name + ' correlations.csv')

  print('scatter')
  scatterPairs = (
    ('raw fourbytes', 'fStat byteBag'),
    ('raw ncd', 'fStat ncd'),
    ('fStat jump', 'skeletons bz'),
    ('fStat0 ppdeep_mod', 'fStat jump'),
    ('fStat0 jump', 'raw ncd'),
    ('skeletons jump', 'fstSecSkel bz'),
    ('fstSecSkel jump', 'raw bz'),
    ('skeletons ncd', 'fStat0 bz'),
    ('fStat0 byteBag', 'fStat byteBag'),
    ('skeletons ncd', 'fStat ncd'),
    ('fstSecSkel ncd', 'skeletons bz'),
    ('fStat0 ncd', 'fStat jump'),
    ('fStat0 ssdeep', 'fStat0 ppdeep_mod'),
  )
  for a, b in scatterPairs:
    plot.saveScatter(df, a, b, title=name + ' scatter', colorBy='isInner')

  for method in methodToPairs.keys():
    test.saveHistogram(df, ' '.join(method), name)
    plot.saveViolin(df, ' '.join(method), name)

if __name__ == '__main__':
  run(lambda m: True, 'all')
  write.saveStr(
    '\n'.join(util.mdImg(f[:-4], f'./{f}') for f in plot.listPngFiles()),
    filename='README.md')
