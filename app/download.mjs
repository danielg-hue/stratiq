export function downloadFile(filename, contents, mediaType) {
  const uri = URL.createObjectURL(new Blob([contents], {type: mediaType}));
  const link = document.createElement('a');
  link.href = uri;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(uri), 1000);
}
