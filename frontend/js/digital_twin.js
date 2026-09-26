class DigitalTwinVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.data = null;
    this.scale = 26; // pixels per meter
    this.offsetX = 50;
    this.offsetY = 50;
    this.hoveredLocation = null;
    this.animationFrame = null;
    this.dashOffset = 0;

    if (this.canvas) {
      this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
      this.canvas.addEventListener('mouseleave', () => {
        this.hoveredLocation = null;
        this.draw();
      });
    }
  }

  setData(twinData) {
    this.data = twinData;
    this.draw();
    this.startAnimation();
  }

  startAnimation() {
    if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
    const animate = () => {
      this.dashOffset -= 0.5;
      this.draw();
      this.animationFrame = requestAnimationFrame(animate);
    };
    this.animationFrame = requestAnimationFrame(animate);
  }

  handleMouseMove(e) {
    if (!this.data || !this.data.locations) return;
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    let found = null;
    for (const loc of this.data.locations) {
      const rx = this.offsetX + loc.x * this.scale;
      const ry = this.offsetY + loc.y * this.scale;
      const rw = 2.4 * this.scale;
      const rh = 1.6 * this.scale;

      if (mouseX >= rx && mouseX <= rx + rw && mouseY >= ry && mouseY <= ry + rh) {
        found = loc;
        break;
      }
    }

    if (found !== this.hoveredLocation) {
      this.hoveredLocation = found;
      this.draw();
    }
  }

  draw() {
    if (!this.ctx || !this.data) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // 1. Draw warehouse floor grid
    ctx.strokeStyle = '#243046';
    ctx.lineWidth = 1;
    for (let x = 0; x < this.canvas.width; x += 30) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < this.canvas.height; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvas.width, y);
      ctx.stroke();
    }

    // 2. Draw Staging / Inbound Dock
    const dockX = this.offsetX + 0.0 * this.scale;
    const dockY = this.offsetY + 0.0 * this.scale;
    ctx.fillStyle = '#1e293b';
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.fillRect(dockX - 10, dockY - 10, 80, 50);
    ctx.strokeRect(dockX - 10, dockY - 10, 80, 50);
    ctx.fillStyle = '#60a5fa';
    ctx.font = '11px sans-serif';
    ctx.fillText('INBOUND DOCK', dockX - 4, dockY + 18);

    // 3. Draw Packing Station
    const packX = this.offsetX + 25.0 * this.scale;
    const packY = this.offsetY + 2.0 * this.scale;
    ctx.fillStyle = '#1e293b';
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.fillRect(packX - 20, packY - 15, 100, 55);
    ctx.strokeRect(packX - 20, packY - 15, 100, 55);
    ctx.fillStyle = '#34d399';
    ctx.font = '11px sans-serif';
    ctx.fillText('PACKING AREA', packX - 14, packY + 18);

    // 4. Draw Racks
    for (const loc of this.data.locations) {
      const rx = this.offsetX + loc.x * this.scale;
      const ry = this.offsetY + loc.y * this.scale;
      const rw = 2.4 * this.scale;
      const rh = 1.6 * this.scale;

      // Color coding per status
      let fillCol = '#1e293b';
      let strokeCol = '#475569';
      let badgeText = '';

      if (loc.status_color === 'dead_stock') {
        fillCol = 'rgba(239, 68, 68, 0.3)';
        strokeCol = '#ef4444';
        badgeText = 'DEAD';
      } else if (loc.status_color === 'expiring') {
        fillCol = 'rgba(245, 158, 11, 0.3)';
        strokeCol = '#f59e0b';
        badgeText = 'EXP';
      } else if (loc.status_color === 'high_pick') {
        fillCol = 'rgba(16, 185, 129, 0.25)';
        strokeCol = '#10b981';
        badgeText = 'HOT';
      } else if (loc.status_color === 'high_stock') {
        fillCol = 'rgba(99, 102, 241, 0.25)';
        strokeCol = '#6366f1';
      }

      ctx.fillStyle = fillCol;
      ctx.strokeStyle = (this.hoveredLocation === loc) ? '#ffffff' : strokeCol;
      ctx.lineWidth = (this.hoveredLocation === loc) ? 3 : 1.5;
      
      ctx.fillRect(rx, ry, rw, rh);
      ctx.strokeRect(rx, ry, rw, rh);

      // Label rack code
      ctx.fillStyle = '#f8fafc';
      ctx.font = 'bold 11px sans-serif';
      ctx.fillText(loc.code, rx + 6, ry + 16);

      // Occupancy mini bar
      ctx.fillStyle = 'rgba(255,255,255,0.1)';
      ctx.fillRect(rx + 6, ry + 24, rw - 12, 5);
      ctx.fillStyle = strokeCol;
      ctx.fillRect(rx + 6, ry + 24, (rw - 12) * (loc.occupancy_pct / 100), 5);

      if (badgeText) {
        ctx.fillStyle = strokeCol;
        ctx.font = 'bold 9px sans-serif';
        ctx.fillText(badgeText, rx + rw - 30, ry + 15);
      }
    }

    // 5. Draw Active Picking Route overlay if present
    const route = this.data.active_picking_route;
    if (route && route.waypoints && route.waypoints.length > 1) {
      ctx.strokeStyle = '#a855f7';
      ctx.lineWidth = 3;
      ctx.setLineDash([8, 6]);
      ctx.lineDashOffset = this.dashOffset;

      ctx.beginPath();
      for (let i = 0; i < route.waypoints.length; i++) {
        const wp = route.waypoints[i];
        const wx = this.offsetX + wp.x * this.scale + (i > 0 && i < route.waypoints.length - 1 ? 1.2 * this.scale : 0);
        const wy = this.offsetY + wp.y * this.scale + (i > 0 && i < route.waypoints.length - 1 ? 0.8 * this.scale : 0);

        if (i === 0) ctx.moveTo(wx, wy);
        else ctx.lineTo(wx, wy);
      }
      ctx.stroke();
      ctx.setLineDash([]); // Reset line dash

      // Draw waypoints markers
      for (let i = 0; i < route.waypoints.length; i++) {
        const wp = route.waypoints[i];
        const wx = this.offsetX + wp.x * this.scale + (i > 0 && i < route.waypoints.length - 1 ? 1.2 * this.scale : 0);
        const wy = this.offsetY + wp.y * this.scale + (i > 0 && i < route.waypoints.length - 1 ? 0.8 * this.scale : 0);

        ctx.fillStyle = (i === 0) ? '#3b82f6' : (i === route.waypoints.length - 1 ? '#10b981' : '#a855f7');
        ctx.beginPath();
        ctx.arc(wx, wy, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const label = (i === 0) ? 'S' : (i === route.waypoints.length - 1 ? 'E' : `${i}`);
        ctx.fillText(label, wx, wy);
      }
      ctx.textAlign = 'start';
      ctx.textBaseline = 'alphabetic';
    }

    // 6. Draw Tooltip for hovered location
    if (this.hoveredLocation) {
      const loc = this.hoveredLocation;
      const tx = this.offsetX + loc.x * this.scale + 10;
      const ty = this.offsetY + loc.y * this.scale - 10;

      const itemsText = loc.items.map(it => `${it.product_name}: ${it.quantity} ${it.uom}`).join(', ') || 'Empty';
      const tooltipText = `${loc.code} | Occ: ${loc.occupancy_pct}% | ${itemsText}`;

      ctx.font = '12px sans-serif';
      const textWidth = ctx.measureText(tooltipText).width;

      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = '#6366f1';
      ctx.lineWidth = 1;
      ctx.fillRect(tx - 6, ty - 22, textWidth + 16, 28);
      ctx.strokeRect(tx - 6, ty - 22, textWidth + 16, 28);

      ctx.fillStyle = '#ffffff';
      ctx.fillText(tooltipText, tx + 2, ty - 4);
    }
  }
}
