// -*- C++ -*-
#include "Rivet/Analysis.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/ChargedFinalState.hh"
#include "Rivet/Projections/SingleValueProjection.hh"
#include "Rivet/Projections/ImpactParameterProjection.hh"
#include "Rivet/Tools/Percentile.hh"
#include "Rivet/Analyses/RHICCommon.hh"

namespace Rivet {


  /// @brief Third harmonic of azimuthal correlations in Au+Au collisions at different COM energies
  class STAR_2016_I1414638 : public Analysis {
  public:

    /// Constructor
    STAR_2016_I1414638 ()
      : Analysis("STAR_2016_I1414638") {}


    void init() {
      /// Projections
      declareCentrality(STAR_BES_Centrality(), "STAR_BES_CALIB", "CMULT", "CMULT");
      declare(ChargedFinalState(Cuts::abseta < 1.0 && Cuts::pT > 0.2*GeV), "CFS");

      // Histograms
      int energy = -1;
      for (int i = 0, N = energies.size(); i < N; ++i) {
        if (isCompatibleWithSqrtS(197.*energies[i]*GeV, 1e-1)) energy = i;
      }
      if (energy == -1) MSG_ERROR("Incompatible beam energy!");
      for (int i = 0; i < 9; ++i) book(h_v32[centralityBins[i]], 1 + i + 9 * energy, 1, 1);
    }


    /// Perform the per-event analysis
    void analyze(const Event& event) {
      const ChargedFinalState& cfs = apply<ChargedFinalState>(event, "CFS");
      // Require at least two charged particles for the analysis to make sense.
      // No further triggers are described in the paper.
      const Particles& particles = cfs.particles();
      if (particles.size() < 2) return;
      // The centrality projection
      const CentralityProjection& cent = apply<CentralityProjection>(event,"CMULT");
      const double c = cent();
      // Find the correct histogram to fill.
      auto hItr = h_v32.upper_bound(c);
      if (hItr == h_v32.end()) return;
      for (int i = 0, N = particles.size(); i < N; ++i){
        for (int j = i + 1; j < N; ++j) {
          const double eta1 = particles[i].eta();
          const double eta2 = particles[j].eta();
          if (eta1 * eta2 < 0) {
            const double deltaPhi = abs(particles[i].phi() - particles[j].phi());
            // Fill profile with v_2(2)^2 from eq. (1) in the paper.
            hItr->second->fill(abs(eta1 - eta2), cos(3.*deltaPhi));
          }
        }
      }
    }

    /// Normalise histograms etc., after the run
    // void finalize() {}

    /// @}


    /// @name Bin edges
    /// @{
    /// The centrality bins
    const doubles centralityBins = {5., 10., 20., 30., 40., 50., 60., 70., 80.};
    /// The analysis energies
    const doubles energies = {7.7, 11.5, 14.5, 19.6, 27.0, 39.0, 62.4, 200.0};
    /// @}


    /// The histograms
    map<double, Profile1DPtr> h_v32;

  };


  RIVET_DECLARE_PLUGIN(STAR_2016_I1414638);

}
