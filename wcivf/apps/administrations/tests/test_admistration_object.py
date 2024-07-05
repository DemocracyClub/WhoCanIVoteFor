# from administrations.helpers import BASE_DATA_PATH, Administration
#
#
# def test_all_files_parse():
#     for filename in BASE_DATA_PATH.glob("*.json"):
#         admin_class = Administration(filename.stem)
#         has_template = False
#         try:
#             admin_class.responsibilities_template()
#             has_template = True
#         except:
#             raise
#         if not has_template:
#             print(admin_class.admin_id, admin_class.role_name())
