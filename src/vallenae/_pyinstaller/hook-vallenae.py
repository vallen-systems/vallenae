# noqa: N999, invalid module name

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("vallenae", subdir="io/schema_templates", includes=["*.sql"])
