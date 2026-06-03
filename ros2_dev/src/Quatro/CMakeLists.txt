cmake_minimum_required(VERSION 3.10)
project(quatro)

### set compiler
set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_FLAGS "-std=c++17 -fexceptions -g -ggdb -fopenmp -O3 -ftree-vectorize -funroll-loops")
include(FindOpenMP) #The best way to set proper compiler settings for using OpenMP in all platforms
if(OPENMP_FOUND) #The best way to set proper compiler settings for using OpenMP in all platforms
  set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
  set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_EXE_LINKER_FLAGS}")
else()
  message("ERROR: OpenMP could not be found.")
endif(OPENMP_FOUND)
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -Wall ${CMAKE_CXX_FLAGS}")

### get packages
find_package(Eigen3 REQUIRED)
find_package(PCL REQUIRED)
find_package(teaserpp REQUIRED)
if(PCL_FOUND)
  message(WARNING "PCL_VER: ${PCL_VERSION}, and PCL_DIR: ${PCL_INCLUDE_DIRS}")
endif()
if(Eigen3_FOUND)
  message(WARNING "EIGEN_VER: ${EIGEN3_VERSION_STRING}, and Eigen DIR: ${EIGEN3_INCLUDE_DIR}")
endif()
if(teaserpp_FOUND)
  message(WARNING "teaserpp found")
endif()

#### for tbb
option(QUATRO_TBB "Enable TBB support" ON)
if(QUATRO_TBB)
  message(WARNING "Quatro with TBB")
  list(APPEND CMAKE_MODULE_PATH /usr/local/include /usr/include)
  find_library(TBB_LIBRARY tbb HINTS /usr/lib /usr/local/lib)
  message(WARNING "TBB FOUND, ${TBB_LIBRARY}")
  add_definitions(-DTBB_EN)
  include(ProcessorCount)
  ProcessorCount(N)
  message(WARNING "Processer number: ${N}")
  if(N GREATER 4)
    add_definitions(-DTBB_PROC_NUM=${N})
  else()
    add_definitions(-DTBB_PROC_NUM=1)
  endif()
endif()

#### for debug output
if(QUATRO_DEBUG)
  add_definitions(-DQUATRO_DEBUG)
endif()

find_package(ament_cmake REQUIRED)

### get packages' headers
include_directories(
  include
  ${EIGEN3_INCLUDE_DIR}
  ${PCL_INCLUDE_DIRS}
)

###########
## Build ##
###########
### main
add_library(${PROJECT_NAME} src/fpfh.cc src/matcher.cc src/quatro_module.cc)
if(QUATRO_TBB)
  target_link_libraries(${PROJECT_NAME} ${OpenMP_LIBS} ${EIGEN3_LIBS} ${PCL_LIBRARIES} teaserpp::teaser_registration teaserpp::teaser_io ${TBB_LIBRARY})
else()
  target_link_libraries(${PROJECT_NAME} ${OpenMP_LIBS} ${EIGEN3_LIBS} ${PCL_LIBRARIES} teaserpp::teaser_registration teaserpp::teaser_io)
endif()

install(DIRECTORY include/
  DESTINATION include/
)

install(TARGETS ${PROJECT_NAME}
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

ament_export_libraries(
  ${PROJECT_NAME}
)

ament_export_include_directories(
  include
)

ament_package()
