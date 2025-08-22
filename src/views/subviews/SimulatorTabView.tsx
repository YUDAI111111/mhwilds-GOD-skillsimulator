import React from 'react';
export default function SimulatorTabView(){
  return (
    <div className="main" style={{marginTop:8}}>
      <div className="group">
        <div className="group-header"><div className="group-title">検索結果</div></div>
        <table className="table">
          <thead><tr><th>#</th><th>装備</th><th>シリーズ</th><th>合計スキル</th><th>装飾品</th></tr></thead>
          <tbody>
            <tr><td>1</td><td>（未実装）</td><td>-</td><td>-</td><td>-</td></tr>
          </tbody>
        </table>
      </div>
      <div className="sidebar">
        <h3>説明</h3>
        <div className="code">ここに解の一覧を表示します（次段）。</div>
      </div>
    </div>
  );
}
