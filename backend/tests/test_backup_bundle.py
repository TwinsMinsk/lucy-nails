import io
import tarfile

import pytest

from scripts.ops.backup_postgres import bundle_uploads
from scripts.ops.restore_postgres import unpack_bundle


def test_bundle_preserves_database_and_uploaded_files(tmp_path):
    database = tmp_path / "source.dump"
    database.write_bytes(b"sample dump")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "image.webp").write_bytes(b"sample upload")
    archive = tmp_path / "backup.tar"
    bundle_uploads(database, uploads, archive)
    restored = tmp_path / "restored"
    restored.mkdir()
    assert unpack_bundle(archive, restored).read_bytes() == database.read_bytes()
    assert (restored / "uploads/image.webp").read_bytes() == b"sample upload"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "uploads/../../escape"])
def test_bundle_rejects_path_escape(tmp_path, name):
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as bundle:
        entry = tarfile.TarInfo(name)
        entry.size = 1
        bundle.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises(RuntimeError, match="Unsafe backup member"):
        unpack_bundle(archive, tmp_path / "restored")
