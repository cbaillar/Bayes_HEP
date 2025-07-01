// -*- C++ -*-
#include "Rivet/Analysis.hh"
#include "Rivet/Projections/Beam.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/UnstableParticles.hh"
#include "Rivet/Projections/SingleValueProjection.hh"
#include "Rivet/Projections/AliceCommon.hh"
#include "Rivet/Tools/AliceCommon.hh"
#include "Rivet/Projections/HepMCHeavyIon.hh"

namespace Rivet {


  // @brief Sigma(1385) resonance production in PbPb collisions at 5.02 TeV
  class ALICE_2022_I2088201 : public Analysis {
  public:

    /// Constructor
    RIVET_DEFAULT_ANALYSIS_CTOR(ALICE_2022_I2088201);

    /// Book histograms and initialise projections before the run
    void init() {

      // Access the HepMC heavy ion info
      declare(HepMCHeavyIon(), "HepMC");

      // Declare centrality projection
      declareCentrality(ALICE::V0MMultiplicity(), "ALICE_2015_CENT_PBPB", "V0M", "V0M");

      // Charged, primary particles with |y| < 0.5
      declare(ALICE::PrimaryParticles(Cuts::absrap < 0.5 && Cuts::abscharge > 0), "APRIM");

      // Resonances
      declare(UnstableParticles(Cuts::absrap<0.5), "RSN");
      //----------------------------------------------------------------------------------

      //----------------------------------------------------------------------------------
      // Loop over all histograms
      for (size_t ihist = 0; ihist < NHISTOS; ++ihist) {

        std::string nameCounterPbPb = "/TMP/counter." + std::to_string(ihist);
        book(_counterSOW[ihist], nameCounterPbPb); // Sum of weights counter

        // SigmaStarPlus+cc pt spectra in PbPb (Tables 1-3 in HEPData)
        book(_hist_SigmaStarPlus[ihist], ihist+1, 1, 1);

        // SigmaStarMinus+cc pt spectra in PbPb (Tables 4-6 in HEPData)
        book(_hist_SigmaStarMinus[ihist], ihist+4, 1, 1);

      } // end loop


      book(_hist_cent, "/TMP/cent", refData(7, 1, 1));
      book(_hist_ySigmaStarPlus, "/TMP/SigmaStarPlus", refData(7, 1, 1));
      book(_hist_ySigmaStarMinus, "/TMP/SigmaStarMinus", refData(8, 1, 1));

      book(_hist_integrated_yield_SigmaStarPlus, 7, 1, 1);
      book(_hist_integrated_yield_SigmaStarMinus, 8, 1, 1);

      book(_hist_mean_pt_SigmaStarPlus, 9, 1, 1);
      book(_hist_mean_pt_SigmaStarMinus, 10, 1, 1);

      book(_hist_integrated_yield_pion, "/TMP/integrated_yield_pion", refData( 11, 1, 1));
      book(_hist_integrated_yield_SigmaStar, "/TMP/integrated_yield_SigmaStar", refData( 11, 1, 1));
      book(_hist_integrated_SigmaStar_pion_ratio, 11, 1, 1);


    } // end init

    /// Perform the per-event analysis
    void analyze(const Event& event) {

      if (int_edges.empty()) {
        int_edges.push_back(_hist_integrated_yield_pion->bin(1).xMid());
        int_edges.push_back(_hist_integrated_yield_pion->bin(3).xMid());
        int_edges.push_back(_hist_integrated_yield_pion->bin(5).xMid());
      }

      // Charged, primary particles in eta range of |eta| < 0.5
      Particles chargedParticles = apply<ALICE::PrimaryParticles>(event,"APRIM").particlesByPt();

      // Resonances
      const UnstableParticles &rsn = apply<UnstableParticles>(event, "RSN");

      const HepMCHeavyIon & hi = apply<HepMCHeavyIon>(event, "HepMC");
      if (!hi.ok()) {
        MSG_WARNING("HEPMC Heavy ion container needed for this analysis, "
                    "but not found for this event. Skipping.");
        vetoEvent;
      }

      // Prepare centrality projection and value
      const CentralityProjection& centrProj = apply<CentralityProjection>(event, "V0M");
      double centr = centrProj();
      // Veto event for too large centralities since those are not used
      // in the analysis at all
      if ( (centr < 0.) || ((centr > 10.) && (centr < 30.)) || (centr > 90.)) vetoEvent;


      // Fill histograms and add weights based on centrality value
      size_t ihist = 0;
      for (const auto& cent_bin : _hist_cent->bins()) {

        if (cent_bin.isMasked())  continue;

        const double low_edge_SigmaStarPlus = _hist_SigmaStarPlus[ihist]->xMin();
        const double high_edge_SigmaStarPlus = _hist_SigmaStarPlus[ihist]->xMax();
        const double low_edge_SigmaStarMinus = _hist_SigmaStarMinus[ihist]->xMin();
        const double high_edge_SigmaStarMinus = _hist_SigmaStarMinus[ihist]->xMax();
        const double cent_edge = cent_bin.xMid();

        if (inRange(centr, cent_bin.xMin(), cent_bin.xMax())) {

          _counterSOW[ihist]->fill();
          _hist_cent->fill(cent_edge);

          for (const Particle &p : rsn.particles()) {

            int pid = p.abspid();
            if (pid==3224) {

              _hist_ySigmaStarPlus->fill(cent_edge);
              _hist_integrated_yield_SigmaStar->fill(int_edges[2-ihist]);

              double pT = p.pT()/GeV;
              _hist_mean_pt_SigmaStarPlus->fill(cent_edge, pT);

              if (pT > low_edge_SigmaStarPlus && pT < high_edge_SigmaStarPlus) {
                _hist_SigmaStarPlus[ihist]->fill(pT);
              } // condition on pT

            } // is SigmaStarPlus or cc
            else if (pid==3114) {

              _hist_ySigmaStarMinus->fill(cent_edge);
              _hist_integrated_yield_SigmaStar->fill(int_edges[2-ihist]);

              const double pT = p.pT()/GeV;
              _hist_mean_pt_SigmaStarMinus->fill(cent_edge, pT);

              if ( (pT > low_edge_SigmaStarMinus) && (pT < high_edge_SigmaStarMinus)) {
                _hist_SigmaStarMinus[ihist]->fill(pT);
              } // condition on pT

            } // is SigmaStarMinus or cc

          } // end loop over resonances

          for (const Particle& p : chargedParticles) {
            if (p.abspid() == PID::PIPLUS) {
              _hist_integrated_yield_pion->fill(int_edges[2-ihist]);
            }
          }

        } // centrality
        ++ihist;

      } // histo loop

    } // end analyze


    /// Normalise histograms etc., after the run
    void finalize() {

      for (size_t ihist = 0; ihist < NHISTOS; ++ihist) {

        if (_counterSOW[ihist]->sumW() > 0.) {

          scale(_hist_SigmaStarPlus[ihist], (1. / _counterSOW[ihist]->sumW() ));
          scale(_hist_SigmaStarMinus[ihist], (1. / _counterSOW[ihist]->sumW() ));

        }
      } // end loop

      if ( _hist_cent->numEntries() > 0. ) {
        divide(_hist_ySigmaStarPlus, _hist_cent, _hist_integrated_yield_SigmaStarPlus);
        divide(_hist_ySigmaStarMinus, _hist_cent, _hist_integrated_yield_SigmaStarMinus);
      }

      scale( _hist_integrated_yield_SigmaStar, 0.5);
      if ( _hist_integrated_yield_pion->numEntries() > 0. ) {
        divide( _hist_integrated_yield_SigmaStar, _hist_integrated_yield_pion,
          _hist_integrated_SigmaStar_pion_ratio);
      }

    } // end finalize

    static const int NHISTOS = 3;

    Histo1DPtr _hist_SigmaStarPlus[NHISTOS];
    Histo1DPtr _hist_SigmaStarMinus[NHISTOS];
    CounterPtr _counterSOW[NHISTOS];

    Histo1DPtr _hist_cent;

    Histo1DPtr _hist_ySigmaStarPlus;
    Histo1DPtr _hist_ySigmaStarMinus;
    Estimate1DPtr _hist_integrated_yield_SigmaStarPlus;
    Estimate1DPtr _hist_integrated_yield_SigmaStarMinus;

    Histo1DPtr _hist_integrated_yield_SigmaStar;
    Histo1DPtr _hist_integrated_yield_pion;
    Estimate1DPtr _hist_integrated_SigmaStar_pion_ratio;

    Profile1DPtr _hist_mean_pt_SigmaStarPlus;
    Profile1DPtr _hist_mean_pt_SigmaStarMinus;
    vector<double> int_edges;

  };


  RIVET_DECLARE_PLUGIN(ALICE_2022_I2088201);

}
