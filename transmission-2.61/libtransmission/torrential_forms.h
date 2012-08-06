#ifndef _torrential_forms_h_
#define _torrential_forms_h_

void torrentialForms_exportMetaInfo(const tr_torrent *tor) {
  tr_file_index_t i;
  tr_file file;

  fprintf(stderr, "initialized torrent %d: name=%s totalSize=%llu fileCount=%d pieceSize=%u pieceCount=%d\n",
	  tor->uniqueId, tor->info.name, tor->info.totalSize, tor->info.fileCount,
	  tor->info.pieceSize, tor->info.pieceCount);

  for(i = 0; i < tor->info.fileCount; i++) {
    file = tor->info.files[i];
    fprintf(stderr, "TID=%d file=%d offset=%llu length=%llu firstPiece=%u lastPiece=%u name=%s\n",
	    tor->uniqueId, i,
	    file.offset, file.length,
	    file.firstPiece, file.lastPiece, file.name);
  }
}

#endif
