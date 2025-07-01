// -*- C++ -*-
#include "Rivet/Analysis.hh"
#include "Rivet/Projections/ChargedFinalState.hh"

namespace Rivet {


  /// Rivet analysis class for ATLAS 2010 minimum bias analysis
  class ATLAS_2010_I882098 : public Analysis {
  public:

    /// Default constructor
    RIVET_DEFAULT_ANALYSIS_CTOR(ATLAS_2010_I882098);


    /// Initialization, called once before running
    void init() {
      // Projections
      const ChargedFinalState cfs100(Cuts::abseta < 2.5 && Cuts::pT > 100*MeV);
      declare(cfs100, "CFS100");
      const ChargedFinalState cfs500(Cuts::abseta < 2.5 && Cuts::pT > 500*MeV);
      declare(cfs500, "CFS500");
      const ChargedFinalState cfs2500(Cuts::abseta < 2.5 && Cuts::pT > 2500*MeV);
      declare(cfs2500, "CFS2500");

      // Book histograms
      for (double eVal : allowedEnergies()) {

        const string en = toString(int(eVal));
        if (isCompatibleWithSqrtS(eVal))  _sqs = en;

        if (en == "2360") {
          book(_h[en+"pt500_nch1_eta"],  2, 1, 1);
          book(_h[en+"pt500_nch1_pt"],   9, 1, 1);
          book(_h[en+"pt500_nch1_nch"], 16, 1, 1);
          continue;
        }
        bool is7TeV(en  == "7000"s);
        book(_h[en+"pt100_nch2_nch"],   18+is7TeV, 1, 1);
        book(_h[en+"pt100_nch2_pt"],    11+is7TeV, 1, 1);
        book(_h[en+"pt100_nch2_eta"],    4+is7TeV, 1, 1);
        book(_p[en+"pt100_nch2_ptnch"], 24+is7TeV, 1, 1);

        book(_h[en+"pt100_nch20_nch"], 34+is7TeV, 1, 1);
        book(_h[en+"pt100_nch20_pt"],  30+is7TeV, 1, 1);
        book(_h[en+"pt100_nch20_eta"], 26+is7TeV, 1, 1);

        book(_h[en+"pt500_nch1_nch"],   15+(is7TeV? 2 : 0), 1, 1);
        book(_h[en+"pt500_nch1_pt"],     8+(is7TeV? 2 : 0), 1, 1);
        book(_h[en+"pt500_nch1_eta"],    1+(is7TeV? 2 : 0), 1, 1);
        book(_p[en+"pt500_nch1_ptnch"], 22+is7TeV, 1, 1);

        book(_h[en+"pt500_nch6_nch"], 20+is7TeV, 1, 1);
        book(_h[en+"pt500_nch6_pt"],  13+is7TeV, 1, 1);
        book(_h[en+"pt500_nch6_eta"],  6+is7TeV, 1, 1);

        book(_h[en+"pt2500_nch1_nch"],   36+is7TeV, 1, 1);
        book(_h[en+"pt2500_nch1_pt"],    32+is7TeV, 1, 1);
        book(_h[en+"pt2500_nch1_eta"],   28+is7TeV, 1, 1);
        book(_p[en+"pt2500_nch1_ptnch"], 38+is7TeV, 1, 1);
      }
      if (_sqs == "" && !merging()) {
        throw BeamError("Invalid beam energy for " + name() + "\n");
      }
    }


    void analyze(const Event& event) {
      // 100 GeV final states
      if (_sqs != "2360"s) {
        const ChargedFinalState& cfs100 = apply<ChargedFinalState>(event, "CFS100");
        fillPtEtaNch(cfs100, 2, "pt100_nch2"); // nch>=2
        fillPtEtaNch(cfs100, 20, "pt100_nch20"); // nch>=20
      }

      // 500 GeV final states
      const ChargedFinalState& cfs500 = apply<ChargedFinalState>(event, "CFS500");
      fillPtEtaNch(cfs500, 1, "pt500_nch1"); // nch>=1
      if (_sqs != "2360"s) {
        fillPtEtaNch(cfs500, 6, "pt500_nch6"); // nch>=6
      }

      // 2500 GeV final states
      if (_sqs != "2360"s) {
        const ChargedFinalState& cfs2500 = apply<ChargedFinalState>(event, "CFS2500");
        fillPtEtaNch(cfs2500, 1, "pt2500_nch1"); // nch>=1
      }

    }


    void finalize() {

      for (double eVal : allowedEnergies()) {

        const string en = toString(int(eVal));

        double sf = safediv(1.0, _h[en+"pt500_nch1_nch"]->integral(true), 1.0);
        scale(_h[en+"pt500_nch1_nch"], sf);
        scale(_h[en+"pt500_nch1_pt"],  sf/TWOPI/5);
        scale(_h[en+"pt500_nch1_eta"], sf);
        if (en != "2360"s) {
          sf = safediv(1.0, _h[en+"pt100_nch2_nch"]->integral(true), 1.0);
          scale(_h[en+"pt100_nch2_nch"], sf);
          scale(_h[en+"pt100_nch2_pt"],  sf/TWOPI/5);
          scale(_h[en+"pt100_nch2_eta"], sf);

          sf = safediv(1.0, _h[en+"pt100_nch20_nch"]->integral(true), 1.0);
          scale(_h[en+"pt100_nch20_nch"], sf);
          scale(_h[en+"pt100_nch20_pt"],  sf/TWOPI/5);
          scale(_h[en+"pt100_nch20_eta"], sf);

          sf = safediv(1.0, _h[en+"pt500_nch6_nch"]->integral(true), 1.0);
          scale(_h[en+"pt500_nch6_nch"], sf);
          scale(_h[en+"pt500_nch6_pt"],  sf/TWOPI/5);
          scale(_h[en+"pt500_nch6_eta"], sf);

          sf = safediv(1.0, _h[en+"pt2500_nch1_nch"]->integral(true), 1.0);
          scale(_h[en+"pt2500_nch1_nch"], sf);
          scale(_h[en+"pt2500_nch1_pt"],  sf/TWOPI/5);
          scale(_h[en+"pt2500_nch1_eta"], sf);
        }
      }
    }


    /// Helper for collectively filling Nch, pT, eta, and pT vs. Nch histograms
    void fillPtEtaNch(const ChargedFinalState& cfs, const int nchcut, const string& label) {
      // Get number of particles and skip if event fails cut
      const int nch = cfs.size();
      if (nch < nchcut) return;

      // Fill nch
      _h[_sqs+label+"_nch"]->fill(nch);
      // Loop over particles, fill pT, eta and ptnch
      for (const Particle& p : cfs.particles()) {
        const double pt = p.pT();
        _h[_sqs+label+"_pt"]->fill(pt/GeV, 1.0/pt);
        _h[_sqs+label+"_eta"]->fill(p.eta());
        if (_sqs != "2360"s && label != "pt100_nch20"s && label != "pt500_nch6"s) {
          _p[_sqs+label+"_ptnch"]->fill(nch, pt/GeV);
        }
      }
    }

  private:

    map<string, Histo1DPtr> _h;
    map<string, Profile1DPtr> _p;

    string _sqs = "";

  };


  RIVET_DECLARE_ALIASED_PLUGIN(ATLAS_2010_I882098, ATLAS_2010_S8918562);

}
