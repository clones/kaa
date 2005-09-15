#include <vector>

class FilterPlugin;

class FilterChain {
  public:
  std::vector< int > pids;
  std::vector< FilterPlugin* > filterlist;
};

