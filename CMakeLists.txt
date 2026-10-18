cmake_minimum_required(VERSION 3.16)

# the version of the package is the one of pyproject.toml
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/pyproject.toml" PYPROJECT_VERSION
     REGEX "^version = ")
string(REGEX REPLACE "^version = \"([0-9.]+)\".*" "\\1" PYPROJECT_VERSION
       "${PYPROJECT_VERSION}")

# the Debian package of the library; nothing is compiled
project(cyberiadaml-py VERSION ${PYPROJECT_VERSION} LANGUAGES NONE)

# the place of the pure Python packages on Debian
set(PYTHON_INSTALL_DIR "lib/python3/dist-packages" CACHE STRING
    "the directory of the cyberiadaml_py package under the prefix")
set(DOC_INSTALL_DIR "share/doc/python3-cyberiadaml")
# the package directories do not follow the umask of the build
set(CMAKE_INSTALL_DEFAULT_DIRECTORY_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
    GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/cyberiadaml_py
        DESTINATION ${PYTHON_INSTALL_DIR}
        PATTERN "__pycache__" EXCLUDE
        PATTERN "*.pyc" EXCLUDE)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/ChangeLog.md
              ${CMAKE_CURRENT_SOURCE_DIR}/README.md
              ${CMAKE_CURRENT_SOURCE_DIR}/LICENSE
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/ARCHITECTURE.md
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/API.md
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/CML.md
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/TESTING.md
        DESTINATION ${DOC_INSTALL_DIR})

# the machine-readable (DEP-5) copyright, where the Debian policy wants it
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/debian-copyright
        DESTINATION ${DOC_INSTALL_DIR} RENAME copyright)

# the tests need pytest and pydantic in this Python
# (-DPython3_EXECUTABLE=... selects another one)
find_package(Python3 3.10 COMPONENTS Interpreter)
if(Python3_FOUND)
  enable_testing()
  add_test(NAME pytest
           COMMAND ${Python3_EXECUTABLE} -B -m pytest -q -p no:cacheprovider tests
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
endif()

# optional per-release suffix (e.g. ubuntu2604) for the package version: the
# package is tested against that release's Python and pydantic
set(DISTRO_TAG "" CACHE STRING "distribution suffix appended to the package version")
configure_file("${PROJECT_SOURCE_DIR}/CyberiadamlPyPackOptions.cmake.in"
               "${PROJECT_BINARY_DIR}/CyberiadamlPyPackOptions.cmake"
               @ONLY)
set(CPACK_PROJECT_CONFIG_FILE "${PROJECT_BINARY_DIR}/CyberiadamlPyPackOptions.cmake")

include(CPack)
